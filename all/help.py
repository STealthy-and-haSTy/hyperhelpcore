import sublime
import sublime_plugin

from .operations import _log as log
from .operations import scan_packages, reload_package
from .operations import help_view, focus_on, display_help, reload_help
from .operations import show_topic


###----------------------------------------------------------------------------


class HyperHelpCommand(sublime_plugin.ApplicationCommand):
    """
    The core command of hyperhelp; allows you to display help files and topics
    defined in packages that are providing help.
    """
    def __init__(self):
        self._help_list = dict()

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

            show_topic(pkg_info, entry["topic"])

    def show_toc(self, pkg_info, items, stack):
        captions = [[item["caption"], item["topic"] +
            (" ({} topics)".format(len(item["children"])) if "children" in item else "")]
            for item in items]

        if len(captions) == 0 and len(stack) == 0:
            return log("No help topics defined for %s", pkg_info.package,
                       status=True)

        if len(stack) > 0:
            captions.insert(0, ["..", "Go back"])

        sublime.active_window().show_quick_panel(
            captions,
            on_select=lambda index: self.select_toc_item(pkg_info, items, stack, index))

    def select_package_item(self, pkg_list, index):
        if index >= 0:
            self.run(pkg_list[index][0], True)

    def select_package(self):
        if len(self._help_list) <= 1:
            return log("No packages with help are currently installed", status=True)

        pkg_list = sorted([key for key in self._help_list if key != "__scanned"])
        captions = [[self._help_list[key].package,
                     self._help_list[key].description]
            for key in pkg_list]

        sublime.active_window().show_quick_panel(
            captions,
            on_select=lambda index: self.select_package_item(captions, index))

    def reload(self, package, topic):
        if topic == "reload":
            return reload_help(self._help_list)
        self._help_list = reload_package(self._help_list, package)

    def run(self, package=None, toc=False, topic=None, reload=False):
        if "__scanned" not in self._help_list:
            scan_packages(self._help_list)

        if reload == True:
            return self.reload(package, topic)

        # Prompt for a package when no arguments are given
        if package is None and topic is None and toc == False:
            return self.select_package()

        # Collect a missing package from the current help window, if any.
        if package is None:
            view = help_view()
            if view is None:
                return self.select_package()
            package = view.settings().get("_hh_package")

        # Get the help index for the provided package.
        pkg_info = self._help_list.get(package, None)
        if pkg_info is None:
            return log("No help availabie for package %s", package, status=True)

        # Display the table of contents for this help if requested
        if toc:
            return self.show_toc(pkg_info, pkg_info.toc, [])

        # Show the appropriate topic
        show_topic(pkg_info, topic or "index.txt")

    def is_enabled(self, package=None, toc=False, topic=None, reload=False):
        # Always enable unless we're told to display the TOC and:
        #   1) no package is given
        #   2) No help view is currently available to get one from
        if toc == True:
            view = help_view()
            if package is None and view is None:
                return False

        return True


###----------------------------------------------------------------------------


class HyperHelpNavigateCommand(sublime_plugin.WindowCommand):
    """
    Perform all help navigation (with the exception of opening a new help
    topic).
    """
    def run(self, nav, prev=False):
        #TODO: Extend to allow navigation among links, targets or both
        if nav == "link":
            return self.focus_link(prev)

        if nav == "follow":
            return self.follow_link()

        log("Unknown help navigation directive '%s'", nav)

    def follow_link(self):
        topic = self.extract_topic()
        if topic is not None:
            return sublime.run_command("hyper_help", {"topic": topic})

        log("Cannot follow link; no link found under the cursor")

    def focus_link(self, prev):
        view = self.window.active_view()
        point = view.sel()[0].begin()

        targets = view.find_by_selector("meta.link | meta.link-target")
        fallback = targets[-1] if prev else targets[0]

        def pick(pos):
            other = pos.begin()
            return (point < other) if not prev else (point > other)

        for pos in reversed(targets) if prev else targets:
            if pick(pos):
                return focus_on(view, pos)

        focus_on(view, fallback)

    def extract_topic(self):
        view = self.window.active_view()
        point = view.sel()[0].begin()

        if view.match_selector(point, "text.help meta.link"):
            return view.substr(view.extract_scope(point))

        return None

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
                view.window().run_command("hyper_help_navigate", {"nav": "follow"})
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
