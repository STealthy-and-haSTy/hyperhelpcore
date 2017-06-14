import sublime
import sublime_plugin

import re
import webbrowser
import collections

from .output_view import find_view, output_to_view


###----------------------------------------------------------------------------


def log(message, *args, status=False, dialog=False):
    """
    A simple logic facility to ensure that all console output is prefixed with
    the package name so the source is clear. Can also optionally send the output
    to the status line and/or a message dialog.
    """
    message = message % args
    print("HyperHelp:", message)
    if status:
        sublime.status_message(message)
    if dialog:
        sublime.message_dialog(message)


def focus_on_position(view, position):
    """
    Focus the provided view on the given position. Includes some hacks to work
    around a bug in sublime that can sometimes cause it to not properly update
    the window visually.
    """
    position = sublime.Region(position.end(), position.begin())

    view.show_at_center(position)
    view.sel().clear()
    view.sel().add(position)

    # Hack to make the view update properly. See:
    #    https://github.com/SublimeTextIssues/Core/issues/485
    view.add_regions("_hh_rk", [], "", "", sublime.HIDDEN)
    view.erase_regions("_hh_rk")


HelpData = collections.namedtuple("HelpData", ["package", "topics", "toc"])
def load_index_json(package):
    """
    Load a hyperhelp.json file for the given package, which should be in the
    root of the package structure (can be packed or unpacked).

    The return value is a HelpData tuple containing the name of the package,
    the list of topics it contains, and the table of contents, unless there
    is an error loading or parsing the JSON file.
    """
    log("Loading help index for package %s", package)
    def make_help_dict(topic_data, help_file):
        """
        Convert an incoming topic into a dictionary if it's not already.
        """
        # Boolean topics are a shortcut for something whose sole help file is
        # itself.
        if isinstance(topic_data, bool):
            topic_data = help_file

        # String topics use themselves as a caption but link to the given file.
        if isinstance(topic_data, str):
            return (topic_data, {
                "topic": topic_data,
                "caption": topic_data,
                "file": help_file
            })

        # Already a dictionary; fill out with the help file and make sure there
        # is a caption.
        topic = topic_data.get("topic", None)
        topic_data["file"] = help_file
        if "caption" not in topic_data:
            topic_data["caption"] = help_file

        return (topic, topic_data)

    toc_file = "Packages/%s/hyperhelp.json" % package
    try:
        json = sublime.load_resource(toc_file)
        raw_dict = sublime.decode_value(json)

    except:
        return log("Unable to load help index from '%s'", toc_file)

    # Extract all top level dictionary keys that are not considered to be a
    # help file.
    toc = raw_dict.pop("__toc", None)
    topics = dict()

    # TODO: Validate children in the TOC

    for help_file in raw_dict:
        topic_list = raw_dict[help_file]

        if isinstance(topic_list, (bool, str)):
            topic_list = [topic_list]

        for topic_entry in topic_list:
            topic, topic_entry = make_help_dict(topic_entry, help_file)
            if topic is None:
                return log("Entry missing topic in package %s: %s",
                           package, str(topic_entry))

            topics[topic] = topic_entry

    if toc is None:
        toc = [topics.get(topic) for topic in sorted(topics.keys())]

    return HelpData(package, topics, toc)


###----------------------------------------------------------------------------


class HyperHelpCommand(sublime_plugin.ApplicationCommand):
    """
    This command is the core of the help system, and can open a view, follow a
    link target to a new location, or display topic lists.
    """
    def __init__(self):
        self._url_re = re.compile("^(https?|file)://")
        self._help_list = dict()

    def help_content(self, pkg_info, help_file):
        filename = "Packages/%s/doc/%s" % (pkg_info.package, help_file)
        try:
            return sublime.load_resource(filename)
        except:
            pass

        return None

    def topic_file(self, pkg_info, topic):
        return pkg_info.topics.get(topic, {}).get("file", None)

    def show_file(self, pkg_info, help_file):
        window = sublime.active_window()
        view = find_view(window, "HyperHelp")

        if view is not None:
            window.focus_view(view)
            if help_file == view.settings().get("_hh_file", None):
                return view

        help_text = self.help_content(pkg_info, help_file)
        if help_text is not None:
            view = output_to_view(window,
                                  "HyperHelp",
                                  help_text,
                                  syntax="Packages/hyperhelp/all/Help.sublime-syntax")
            view.settings().set("_hh_file", help_file)
            view.settings().set("_hh_package", pkg_info.package)
            return view

        return None

    def show_topic(self, pkg_info, topic):
        help_file = self.topic_file(pkg_info, topic)
        if help_file is None:
            return log("Unknown help topic '%s'", topic, status=True)

        if self._url_re.match(help_file):
            return webbrowser.open_new_tab(help_file)

        if help_file.startswith("Packages/"):
            help_file = help_file.replace("Packages/", "${packages}/")
            window = sublime.active_window()
            return window.run_command("open_file", {"file": help_file})

        help_view = self.show_file(pkg_info, help_file)
        if help_view is None:
            return log("Unable to load help file '%s'", help_file, status=True)

        for pos in help_view.find_by_selector('meta.link-target'):
            target = help_view.substr(pos)
            if target == topic:
                return focus_on_position(help_view, pos)

        log("Unable to find topic '%s' in help file '%s'", topic, help_file,
            status=True)

    def select_toc_item(self, pkg_info, items, stack, index):
        if index >= 0:
            # When stack is not empty, first item takes us back
            if index == 0 and len(stack) > 0:
                items = stack.pop()
                return self.show_toc(pkg_info, items, stack)

            # Compensate for the ".." entry on a non-empty stack
            if len(stack) > 0:
                index -= 1

            entry = items[index]
            children = entry.get("children", None)

            if children is not None:
                stack.append(items)
                return self.show_toc(pkg_info, children, stack)

            self.show_topic(pkg_info, entry["topic"])

    def show_toc(self, pkg_info, items, stack):
        captions = [[item["caption"], item["topic"] +
            (" ({} topics)".format(len(item["children"])) if "children" in item else "")]
            for item in items]

        if len(stack) > 0:
            captions.insert(0, ["..", "Go back"])

        sublime.active_window().show_quick_panel(
            captions,
            on_select=lambda index: self.select_toc_item(pkg_info, items, stack, index))

    def extract_topic(self):
        view = sublime.active_window().active_view()
        point = view.sel()[0].begin()

        if view.match_selector(point, "text.help meta.link"):
            return view.substr(view.extract_scope(point))

        return None

    def run(self, package="hyperhelp", toc=False, topic=None):
        # Get the information on the package to display help for. If it's not
        # known already, try to load it now.
        pkg_info = self._help_list.get(package, None)
        if pkg_info is None:
            result = load_index_json(package)
            if result is not None:
                self._help_list[package] = result
                pkg_info = result
            else:
                return

        if toc:
            return self.show_toc(pkg_info, pkg_info.toc, [])

        if topic is None:
            topic = self.extract_topic() or "index.txt"

        self.show_topic(pkg_info, topic)


###----------------------------------------------------------------------------


class HyperHelpNavigateCommand(sublime_plugin.WindowCommand):
    """
    Advance the cursor to the next or previous link/link target in the document,
    wrapping around the buffer as needed.
    """
    def run(self, prev=False):
        view = self.window.active_view()
        point = view.sel()[0].begin()

        targets = view.find_by_selector("meta.link | meta.link-target")
        fallback = targets[-1] if prev else targets[0]

        def pick(pos):
            other = pos.begin()
            return (point < other) if not prev else (point > other)

        for pos in reversed(targets) if prev else targets:
            if pick(pos):
                return focus_on_position(view, pos)

        focus_on_position(view, fallback)


###----------------------------------------------------------------------------


class HyperHelpListener(sublime_plugin.EventListener):
    def on_text_command(self, view, command, args):
        """
        Listen for double clicks in help files and, if they occur over links,
        follow the link instead of selecting the text.
        """
        if command == "drag_select" and args.get("by", None) == "words":
            event = args["event"]
            point = view.window_to_text((event["x"], event["y"]))

            if view.match_selector(point, "text.help meta.link"):
                sublime.run_command("hyper_help")
                return ("noop")

        return None

    def on_query_context(self, view, key, operator, operand, match_all):
        """
        Allow key bindings in help windows to detect if they are currently in
        help "authoring" mode so that it is possible to edit files without
        the bindings getting in the way.
        """
        if key != "help_author_mode":
            return None

        lhs = view.is_read_only() == False
        rhs = bool(operand)

        if operator == sublime.OP_EQUAL:
            return lhs == rhs
        elif operator == sublime.OP_NOT_EQUAL:
            return lhs != rhs

        return None



###----------------------------------------------------------------------------
