import sublime
import sublime_plugin

from .core import parse_anchor_body, parse_link_body
from .core import help_index_list, lookup_help_topic
from .common import current_help_package


###----------------------------------------------------------------------------


class HyperhelpInternalProcessCommentsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in reversed(self.view.find_by_selector("comment")):
            self.view.erase(edit, region)

    def is_enabled(self):
        return (self.view.match_selector(0, "text.hyperhelp.help") and
                self.view.settings().get("_hh_post_processing", False))


class HyperhelpInternalProcessAnchorsCommand(sublime_plugin.TextCommand):
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
                self.view.settings().get("_hh_post_processing", False))


class HyperhelpInternalProcessLinksCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v = self.view
        v.add_regions("_hh_links", v.find_by_selector("meta.link"), "",
                      flags=sublime.HIDDEN | sublime.PERSISTENT)

        default_pkg = current_help_package(self.view)

        tmp = {}
        regions = v.get_regions("_hh_links")
        for idx,region in enumerate(reversed(regions)):
            pkg_name, topic, text = parse_link_body(v.substr(region))
            pkg_name = pkg_name or default_pkg

            if text is None:
                topic = "_broken"
                text = "broken"

            v.replace(edit, region, text)
            tmp[len(regions) - idx - 1] = {
                "pkg": pkg_name,
                "topic": topic
            }

        hh_links = {}
        active = []
        broken = []

        regions = v.get_regions("_hh_links")
        for idx, region in enumerate(regions):
            hh_links[str(region.begin())] = tmp[idx]

            pkg_info = help_index_list().get(tmp[idx]["pkg"], None)
            if lookup_help_topic(pkg_info, tmp[idx]["topic"]) is not None:
                active.append(region)
            else:
                broken.append(region)

        v.settings().set("_hh_links", hh_links)

        v.add_regions("_hh_links_active", active, "storage",
            flags=sublime.DRAW_SOLID_UNDERLINE | sublime.PERSISTENT |
                  sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

        v.add_regions("_hh_links_broken", broken, "comment",
            flags=sublime.DRAW_STIPPLED_UNDERLINE | sublime.PERSISTENT |
                  sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

    def is_enabled(self):
        return (self.view.match_selector(0, "text.hyperhelp.help") and
                self.view.settings().get("_hh_post_processing", False))


###----------------------------------------------------------------------------
