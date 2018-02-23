import sublime
import sublime_plugin

import os

from .common import log, current_help_package, help_package_prompt
from .view import find_help_view, focus_on
from .core import help_index_list
from .core import show_help_topic, navigate_help_history
from .help import HistoryData

###----------------------------------------------------------------------------


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
    def run(self, package=None, prompt=False):
        package = package or current_help_package()
        if package is None or prompt:
            return help_package_prompt(help_index_list(),
                                       on_select=lambda pkg: self.run(pkg))

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
        anchors = help_view.settings().get("_hh_nav")
        if not anchors:
            return

        point = help_view.sel()[0].begin()
        fallback = anchors[-1] if prev else anchors[0]

        pick = lambda p: (point < p[1][0]) if not prev else (point > p[1][0])
        for pos in reversed(anchors) if prev else anchors:
            if pick(pos):
                return focus_on(help_view, pos[1])

        focus_on(help_view, fallback[1])

    def follow_link(self):
        help_view = find_help_view()
        point = help_view.sel()[0].begin()
        if help_view.match_selector(point, "text.hyperhelp meta.link"):
            topic = help_view.substr(help_view.extract_scope(point))

            package = help_view.settings().get("_hh_pkg")
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

        return help_fmt % package


###----------------------------------------------------------------------------
