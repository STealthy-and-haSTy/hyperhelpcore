import sublime
import sublime_plugin

from .core import parse_anchor_body
from .core import help_index_list, lookup_help_topic
from .common import current_help_package


###----------------------------------------------------------------------------


class HyperhelpInternalCaptureAnchorsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v = self.view
        v.add_regions("_hh_anchors", v.find_by_selector("meta.anchor"), "",
                     flags=sublime.HIDDEN | sublime.PERSISTENT)

        for pos in reversed(v.find_by_selector("punctuation.anchor.hidden")):
            v.erase(edit, pos)

        hh_nav = {}
        regions = v.get_regions("_hh_anchors")
        for idx, region in enumerate(reversed(regions)):
            topic, text = parse_anchor_body(v.substr(region))
            v.replace(edit, region, text)
            hh_nav[topic] = len(regions) - idx - 1

        v.settings().set("_hh_nav", hh_nav)

    def is_enabled(self):
        return (self.view.match_selector(0, "text.hyperhelp.help") and
                self.view.settings().get("_hh_processing_enabled", False))


class HyperhelpInternalCaptureLinksCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        active = []
        broken = []

        hh_links = {}

        for region in reversed(self.view.find_by_selector("meta.link")):
            topic = self.view.substr(region)
            pkg_name = current_help_package(self.view)

            hh_links[str(region.begin())] = {
                "pkg": pkg_name,
                "topic": topic
            }

            pkg_info = help_index_list().get(pkg_name, None)
            if lookup_help_topic(pkg_info, topic) is not None:
                active.append(region)
            else:
                broken.append(region)

        self.view.settings().set("_hh_links", hh_links)

        self.view.add_regions("_hh_links_active", active, "storage",
            flags=sublime.DRAW_SOLID_UNDERLINE | sublime.PERSISTENT |
                  sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

        self.view.add_regions("_hh_links_broken", broken, "comment",
            flags=sublime.DRAW_STIPPLED_UNDERLINE | sublime.PERSISTENT |
                  sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

    def is_enabled(self):
        return (self.view.match_selector(0, "text.hyperhelp.help") and
                self.view.settings().get("_hh_processing_enabled", False))


###----------------------------------------------------------------------------
