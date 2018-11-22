import sublime
import sublime_plugin

import os

from .common import log, hh_setting, hh_update_setting, help_package_prompt
from .common import current_help_file, current_help_package
from .view import find_help_view
from .core import help_index_list, lookup_help_topic
from .core import show_help_topic, navigate_help_history
from .core import parse_anchor_body
from .help import HistoryData, _get_link_topic


###----------------------------------------------------------------------------


def _get_bookmarks():
    """
    Get the list of user bookmarks from the settings file as a list of bookmark
    dictionaries. This list may be empty if the user has not defined any
    bookmarks yet.
    """
    return hh_setting("bookmarks")


def _add_bookmark(bookmark):
    """
    Given a valid bookmark dictionary, add it to the list of user bookmarks in
    the settings file.
    """
    bookmarks = _get_bookmarks()
    bookmarks.append(bookmark)
    hh_update_setting("bookmarks", bookmarks, save=True)


def _bookmark_name(bookmark):
    """
    Given a bookmark dictionary, return back the name of that bookmark. If the
    bookmark has no defined name, one will be returned.
    """
    if bookmark is None:
        return "No bookmark"

    if "name" in bookmark:
        return bookmark["name"]

    pkg_info = help_index_list().get(bookmark.get("package"))
    topic = lookup_help_topic(pkg_info, bookmark.get("topic", ''))

    if topic is None:
        return "Bookmark specifies invalid topic"

    if topic["topic"] in pkg_info.help_files:
        return pkg_info.help_files[topic["topic"]]

    return topic.get("caption", "Caption is missing")



def _bookmark_at_index(bookmark_idx, displayError=False):
    """
    Return the bookmark dictionary for the user bookmark at the given index, if
    any. None is returned if the index is invalid. The optional argument can be
    used to signal an error in the status line if the bookmark index is
    invalid.
    """
    all_bookmarks = _get_bookmarks()
    try:
        return all_bookmarks[bookmark_idx]

    except IndexError:
        if displayError:
            log("Bookmark index was out of range", status=True)

        return None


###----------------------------------------------------------------------------


class BookmarkIdxInputHandler(sublime_plugin.ListInputHandler):
    """
    Allow the user to select an appropriate bookmark index by displaying a list
    of all bookmarks by name.
    """
    def list_items(self):
        return [(_bookmark_name(bmark), idx)
                for idx, bmark in enumerate(_get_bookmarks())]


class BookmarkTypeInputHandler(sublime_plugin.ListInputHandler):
    """
    Allow the user to select what type of bookmark they want to create by
    displaying a list of the available bookmark types that are valid in the
    current context.
    """
    names = {
        "file": "Current file",
        "topic": "Current topic",
        "view": "Current view"
    }
    descs = {
        "file": "Bookmark the current help file",
        "topic": "Bookmark the topic currently under the cursor",
        "view": "Bookmark the current help view"
    }

    def __init__(self, help_view):
        super().__init__()
        self.view = help_view

    def name(self):
        return "bmark_type"

    def placeholder(self):
        return "bookmark type"

    def preview(self, value):
        return sublime.Html("<strong>{}</strong>: <em>{}</em>".format(
            self.names.get(value, "unknown"),
            self.descs.get(value, "unknown")
        ))

    def list_items(self):
        items = [
            ("this file", "file"),
            ("this view", "view")
        ]

        if len(self.view.sel()) > 0:
            pt = self.view.sel()[0].b
            if self.view.match_selector(pt, "meta.link"):
                items.insert(1, ("this topic", "topic"))

        return items

    def validate(self, value):
        self.bmark_type = value
        return True

    def next_input(self, args):
        if args.get("bmark_name") is None:
            return BookmarkNameInputHandler(find_help_view(), self.bmark_type)


class BookmarkNameInputHandler(sublime_plugin.TextInputHandler):
    """
    Allow the user to select a name for their bookmark, showing a default name
    based on the current context and bookmark type.
    """
    def __init__(self, help_view, bmark_type):
        super().__init__()
        self.view = help_view
        self.bmark_type = bmark_type

    def name(self):
        return "bmark_name"

    def placeholder(self):
        return "bookmark name"

    def preview(self, text):
        return "The name for this bookmark"

    def initial_text(self):
        v = self.view

        link_info = None
        if len(v.sel()) > 0 and v.match_selector(v.sel()[0].b, "meta.link"):
            link_info = _get_link_topic(v, v.extract_scope(v.sel()[0].b))

        if self.bmark_type == "topic" and link_info is not None:
            pkg_info = help_index_list().get(link_info["pkg"])
            if pkg_info is not None:
                topic = lookup_help_topic(pkg_info, link_info["topic"])
                return topic["caption"]

        file = current_help_file()
        name = "File {} in help package {}".format(file, current_help_package())
        pkg_info = help_index_list().get(current_help_package())

        if pkg_info is not None and file in pkg_info.help_files:
            name = pkg_info.help_files[file]

        if self.bmark_type == "view":
            name = name + " (view)"

        return name


###----------------------------------------------------------------------------


class HyperhelpFocusCommand(sublime_plugin.TextCommand):
    """
    Alter the selection in the given view (which should be a help view but
    doesn't need to be) by clearing it and setting the single selection to the
    provided position and focusing that position in the view.

    Position may be a single integer or a region.
    """
    def run(self, edit, position, at_center=False):
        if isinstance(position, int):
            position = sublime.Region(position)
        elif isinstance(position, list):
            position = sublime.Region(position[0], position[1])

        if at_center:
            self.view.show_at_center(position)
        else:
            self.view.show(position, True)

        self.view.sel().clear()
        self.view.sel().add(position)


class HyperhelpTopicCommand(sublime_plugin.ApplicationCommand):
    """
    Display the provided help topic inside the given package. If package is
    None, infer it from the currently active help view.
    """
    def run(self, package=None, topic="index.txt"):
        package = package or current_help_package()
        topic = topic or "index.txt"

        if package is None:
            return log("Cannot display topic '%s'; cannot determine package",
                topic, status=True)

        show_help_topic(package, topic, history=True)


class HyperhelpOpenBookmarkCommand(sublime_plugin.ApplicationCommand):
    """
    Navigate to a given bookmark for the user.
    """
    def run(self, bookmark_idx):
        all_bookmarks = hh_setting("bookmarks")
        try:
            bookmark = all_bookmarks[bookmark_idx]
        except IndexError:
            return log("Bookmark index was out of range", status=True)

        pkg = bookmark.get("package")
        topic = bookmark.get("topic")
        caret = bookmark.get("caret")
        viewport = bookmark.get("viewport")

        if pkg is None or topic is None:
            return log("Bookmark at index specified is not valid", status=True)

        if show_help_topic(pkg, topic, history=True) == "file":
            help_view = find_help_view()
            if caret is not None:
                help_view.sel().clear()
                help_view.sel().add(sublime.Region(caret[0], caret[1]))

                if viewport is not None:
                    help_view.set_viewport_position(viewport, True)
                else:
                    help_view.show_at_center(help_view.sel()[0])

    def description(self, bookmark_idx=None):
        bmark = _bookmark_at_index(bookmark_idx)
        return (_bookmark_name(bmark) if bmark is not None
                                      else "Invalid Bookmark Index")

    def input(self, args):
        if args.get("bookmark_idx") is None:
            return BookmarkIdxInputHandler()


class HyperhelpPromptCreateBookmarkCommand(sublime_plugin.ApplicationCommand):
    """
    Interactively prompt the user to create a bookmark, asking them if they
    want to bookmark the current file, the current viewport or the topic that
    the link under the cursor would display.

    This invokes the actual command to create a bookmark if the user follows
    all interctive prompts.
    """
    def run(self, bmark_type, bmark_name):
        v = find_help_view(sublime.active_window())

        link_info = None
        if len(v.sel()) > 0 and v.match_selector(v.sel()[0].b, "meta.link"):
            link_info = _get_link_topic(v, v.extract_scope(v.sel()[0].b))

        pkg_name = current_help_package()
        topic = current_help_file()

        if bmark_type == "topic" and link_info is not None:
            pkg_name = link_info["pkg"]
            topic = link_info["topic"]

        caret = (v.sel()[0].a, v.sel()[0].b) if bmark_type == "view" else None
        viewport = v.viewport_position() if bmark_type == "view" else None

        sublime.run_command("hyperhelp_create_bookmark", {
            "name": bmark_name,
            "package": pkg_name,
            "topic": topic,
            "caret": caret,
            "viewport": viewport
            })

    def is_enabled(self, *kwargs):
        window = sublime.active_window()
        current_view = window.active_view() if window is not None else None
        help_view = find_help_view(window)

        return (current_view == help_view and
                current_view is not None and
                help_index_list().get(current_help_package()) is not None)

    def input_description(self):
        return "Create Bookmark"

    def input(self, args):
        bmark_type = args.get("bmark_type")
        if bmark_type is None:
            return BookmarkTypeInputHandler(find_help_view())

        if args.get("bmark_name") is None:
            return BookmarkNameInputHandler(find_help_view(), bmark_type)


class HyperhelpContextCreateBookmarkCommand(sublime_plugin.TextCommand):
    def run(self, edit, event=None):
        if event is not None:
            point = self.view.window_to_text((event["x"], event["y"]))
            bmark_type = "file"
            if self.view.match_selector(point, "meta.link"):
                bmark_type = "topic"
                self.view.sel().clear()
                self.view.sel().add(sublime.Region(point))

            sublime.run_command("hyperhelp_prompt_create_bookmark", {
                "bmark_type": bmark_type})
        else:
            log("Cannot create a context sensitive bookmark without the mouse",
                status=True)

    def description(self, event=None):
        v = self.view
        if event is not None:
            point = v.window_to_text((event["x"], event["y"]))
            if v.match_selector(point, "meta.link"):
                return "HyperHelp: Bookmark this link"

        return "HyperHelp: Bookmark this file"

    def want_event(self):
        return True

    def is_enabled(self, event=None):
        return self.view.match_selector(0, "text.hyperhelp.help")

    def is_visible(self, event=None):
        return self.is_enabled(event)


class HyperhelpCreateBookmarkCommand(sublime_plugin.ApplicationCommand):
    """
    Does the work of actually creating a bookmark using the given information,
    which is assumed to be correct and is not validated prior to generating the
    new bookmark entry.
    """
    def run(self, name, package, topic, caret=None, viewport=None):
        bookmark = {
            "name": name,
            "package": package,
            "topic": topic
        }

        if caret is not None:
            bookmark["caret"] = caret

            if viewport is not None:
                bookmark["viewport"] = viewport

        _add_bookmark(bookmark)


class HyperhelpContentsCommand(sublime_plugin.ApplicationCommand):
    """
    Display the table of contents for the package provided. If no package is
    given and one cannot be inferred from the current help view, the user will
    be prompted to supply one. The prompt always occurs if the argument asks.
    """
    def run(self, package=None, prompt=False):
        package = package or current_help_package()
        if package is None or prompt:
            return help_package_prompt(help_index_list(),
                                       on_select=lambda pkg: self.run(pkg))

        pkg_info = help_index_list().get(package, None)
        if pkg_info is None:
            return log("Cannot display table of contents; unknown package '%s",
                       package, status=True)

        self.show_toc(pkg_info, pkg_info.help_toc, [])

    def is_enabled(self, package=None, prompt=False):
        if prompt == False:
            package = package or current_help_package()
            if package is None:
                return False

        return True

    def show_toc(self, pkg_info, items, stack):
        captions = [[item["caption"], item["topic"] +
            (" ({} topics)".format(len(item["children"])) if "children" in item else "")]
            for item in items]

        if not captions and not stack:
            return log("No help topics defined for package '%s'",
                       pkg_info.package, status=True)

        if stack:
            captions.insert(0, ["..", "Go back"])

        sublime.active_window().show_quick_panel(
            captions,
            on_select=lambda index: self.select(pkg_info, items, stack, index))

    def select(self, pkg_info, items, stack, index):
        if index >= 0:
            # When the stack isn't empty, the first item takes us back.
            if index == 0 and len(stack) > 0:
                items = stack.pop()
                return self.show_toc(pkg_info, items, stack)

            # Compenstate for the "go back" item when the stack's not empty
            if len(stack) > 0:
                index -= 1

            entry = items[index]
            children = entry.get("children", None)

            if children is not None:
                stack.append(items)
                return self.show_toc(pkg_info, children, stack)

            show_help_topic(pkg_info.package, entry["topic"], history=True)


class HyperhelpIndexCommand(sublime_plugin.ApplicationCommand):
    """
    Display the index for the package provided. If no package is given and one
    cannot be inferred from the current help view, the user will be prompted to
    supply one. The prompt always occurs if the argument asks.
    """
    def run(self, package=None, initial_text=None, prompt=False):
        package = package or current_help_package()
        if package is None or prompt:
            return help_package_prompt(help_index_list(),
                                       on_select=lambda pkg:
                                           self.run(pkg, initial_text))

        pkg_info = help_index_list().get(package, None)
        if pkg_info is None:
            return log("Cannot display topic index; unknown package '%s",
                       package, status=True)

        topics = [pkg_info.help_topics.get(topic)
                  for topic in sorted(pkg_info.help_topics.keys())]

        items = [[t["caption"], t["topic"]]
                 for t in topics]

        if not items:
            return log("No help topics defined for package '%s'",
                       package, status=True)

        sublime.active_window().show_quick_panel(
            items,
            on_select=lambda index: self.select(pkg_info, items, index))

        if initial_text:
            sublime.active_window().run_command("insert", {"characters": initial_text})

    def is_enabled(self, package=None, prompt=False):
        if prompt == False:
            package = package or current_help_package()
            if package is None:
                return False

        return True

    def select(self, pkg_info, items, index):
        if index >= 0:
            show_help_topic(pkg_info.package, items[index][1], history=True)


class HyperhelpNavigateCommand(sublime_plugin.WindowCommand):
    """
    Perform navigation from within a help file
    """
    available_nav = ["find_anchor", "follow_link", "follow_history"]

    def run(self, nav, prev=False):
        if nav == "find_anchor":
            return self.anchor_nav(prev)
        elif nav == "follow_link":
            return self.follow_link()

        navigate_help_history(find_help_view(), prev)

    def is_enabled(self, nav, prev=False):
        help_view = find_help_view()
        if help_view is None or nav not in self.available_nav:
            return False

        if nav == "follow_history":
            settings = help_view.settings()
            h_pos = settings.get("_hh_hist_pos")
            h_len = len(settings.get("_hh_hist"))

            if (prev and h_pos == 0) or (not prev and h_pos == h_len - 1):
                return False

        return True

    def description(self, nav, prev=False):
        # Docs say to return None, but that makes Sublime log an error.
        if nav != "follow_history":
            return ""

        template = "Back" if prev else "Forward"
        help_view = find_help_view()

        if help_view is None:
            return template

        settings = help_view.settings()
        h_pos = settings.get("_hh_hist_pos")
        h_info = settings.get("_hh_hist")

        if (prev and h_pos == 0) or (not prev and h_pos == len(h_info) - 1):
            return template

        entry = HistoryData._make(h_info[h_pos + (-1 if prev else 1)])
        return "%s: %s" % (template, entry.file)

    def anchor_nav(self, prev):
        help_view = find_help_view()
        anchors = help_view.get_regions("_hh_anchors")
        if not anchors:
            return

        point = help_view.sel()[0].begin()
        fallback = anchors[-1] if prev else anchors[0]

        pick = lambda p: (point < p.a) if not prev else (point > p.a)
        for pos in reversed(anchors) if prev else anchors:
            if pick(pos):
                return help_view.run_command("hyperhelp_focus",
                    {"position": [pos.b, pos.a]})

        help_view.run_command("hyperhelp_focus",
            {"position": [fallback.b, fallback.a]})

    def follow_link(self):
        help_view = find_help_view()
        point = help_view.sel()[0].begin()

        if help_view.match_selector(point, "text.hyperhelp meta.link"):
            topic = "_broken"
            package = help_view.settings().get("_hh_pkg")

            link_region = help_view.extract_scope(point)
            topic_dat = _get_link_topic(help_view, link_region)
            if topic_dat is not None:
                topic = topic_dat["topic"]
                package = topic_dat["pkg"] or package

            show_help_topic(package, topic, history=True)


class HyperhelpCurrentHelpCommand(sublime_plugin.WindowCommand):
    """
    This command does nothing, but it's description method tells you what
    help package is currently being browsed, if any.
    """
    def is_enabled(self, **kwargs):
        return False

    def description(self, no_help_fmt="No help currently visible",
                          help_fmt="Viewing help for: '%s'"):
        package = current_help_package(window=self.window)
        if package is None:
            return no_help_fmt

        pkg_info = help_index_list().get(package)
        package = package if pkg_info is None else pkg_info.description
        return help_fmt % package


###----------------------------------------------------------------------------
