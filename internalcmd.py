import sublime
import sublime_plugin

from .core import parse_anchor_body


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


###----------------------------------------------------------------------------
