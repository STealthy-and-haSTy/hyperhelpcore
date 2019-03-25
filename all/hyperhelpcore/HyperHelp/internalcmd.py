import sublime
import sublime_plugin

import time

from hyperhelpcore.core import parse_help_header, parse_anchor_body, parse_link_body
from hyperhelpcore.core import help_index_list, lookup_help_topic
from hyperhelpcore.core import is_topic_file, is_topic_file_valid
from hyperhelpcore.help import _get_link_topic
from hyperhelpcore.common import hh_setting
from hyperhelpcore.common import current_help_package, current_help_file


###----------------------------------------------------------------------------


def _can_post_process(view):
    """
    Determine if the provided view is eligible for a post processing command to
    execute within it or not.
    """
    return (view.match_selector(0, "text.hyperhelp.help") and
            view.settings().get("_hh_post_processing", False))


###----------------------------------------------------------------------------


class HyperhelpInternalProcessHeaderCommand(sublime_plugin.TextCommand):
    """
    Process the header in a newly loaded help file by finding and replacing the
    source level meta header with the fully expanded user-facing header.

    Nothing happens if the current file does not appear to have an appropriate
    meta-header line.
    """
    def run(self, edit):
        help_file = current_help_file(self.view)
        first_line = self.view.substr(self.view.full_line(0))

        header = parse_help_header(help_file, first_line)
        if header is None:
            return

        _hdr_width = 80
        _time_fmt = hh_setting("hyperhelp_date_format")

        file_target = "*%s*" % help_file
        title = header.title
        date_str = "Not Available"

        if header.date != 0:
            date_str = time.strftime(_time_fmt, time.localtime(header.date))

        # Take into account two extra spaces on either side of the title
        max_title_len = _hdr_width - len(file_target) - len(date_str) - 4
        if len(title) > max_title_len:
            title = title[:max_title_len-1] + '\u2026'

        header_line = "%s  %s  %s\n%s\n" % (
            file_target,
            "%s" % title.center(max_title_len, " "),
            date_str,
            ("=" * _hdr_width)
        )

        self.view.replace(edit, self.view.full_line(0), header_line)

    def is_enabled(self):
        return _can_post_process(self.view)


class HyperhelpInternalProcessCommentsCommand(sublime_plugin.TextCommand):
    """
    Remove all hyperhelp comments from a newly loaded help file.

    All text scoped as a comment (including newlines) will be redacted from the
    file.
    """
    def run(self, edit):
        for region in reversed(self.view.find_by_selector("comment.block.help")):
            self.view.erase(edit, region)

    def is_enabled(self):
        return _can_post_process(self.view)


class HyperhelpInternalProcessAnchorsCommand(sublime_plugin.TextCommand):
    """
    Process all anchors in a newly loaded help file. This does the work of
    rewriting anchors so that only their anchor text appears as well as
    removing the markup that makes hidden anchors hidden.

    This results in regions and settings being applied to the view that allow
    the help core to navigate within the file.
    """
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
        return _can_post_process(self.view)


class HyperhelpInternalProcessLinksCommand(sublime_plugin.TextCommand):
    """
    Process all links in a newly loaded help file. This does the work of
    rewriting links so that only their link text appears, while keeping track
    of the topic ID and package designations of each link.

    This results in regions and settings being applied to the view that allow
    the help core to navigate within the file.
    """
    def run(self, edit):
        v = self.view
        regions = v.find_by_selector("meta.link")
        default_pkg = current_help_package(self.view)

        v.add_regions("_hh_links", regions, "",
                      flags=sublime.HIDDEN | sublime.PERSISTENT)


        hh_links = [None] * len(regions)
        for idx,region in enumerate(reversed(regions)):
            base_text = v.substr(region)
            pkg_name, topic, text = parse_link_body(base_text)
            pkg_name = pkg_name or default_pkg

            if text is None:
                topic = "_broken"
                text = base_text

            v.replace(edit, region, text)
            hh_links[len(regions) - idx - 1] = {
                "pkg": pkg_name,
                "topic": topic
            }

        v.settings().set("_hh_links", hh_links)

        v.run_command("hyperhelp_internal_flag_links")

    def is_enabled(self):
        return _can_post_process(self.view)


class HyperhelpInternalFlagLinksCommand(sublime_plugin.TextCommand):
    """
    Given a help file which has had its links post processed already via
    hyperhelp_internal_process_links, this checks each link in the file and
    classifies them as either active or broken, depending on whether or not
    they point to a valid destination.

    This is a non-destructive command and may be executed any time the
    underlying help indexes may have changed, such as at Sublime startup.
    """
    def run(self, edit):
        v = self.view
        active = []
        broken = []

        regions = v.get_regions("_hh_links")
        for idx, region in enumerate(regions):
            link_dat = _get_link_topic(v, idx)

            pkg_info = help_index_list().get(link_dat["pkg"], None)
            topic = lookup_help_topic(pkg_info, link_dat["topic"])

            if self.link_is_active(pkg_info, topic):
                active.append(region)
            else:
                broken.append(region)

        v.add_regions("_hh_links_active", active, "storage",
            flags=sublime.DRAW_SOLID_UNDERLINE | sublime.PERSISTENT |
                  sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

        v.add_regions("_hh_links_broken", broken, "comment",
            flags=sublime.DRAW_STIPPLED_UNDERLINE | sublime.PERSISTENT |
                  sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

    def link_is_active(self, pkg_info, topic):
        if topic is None:
            return False

        # Returns None if the topic is not a file, so only consider the topic
        # broken when the return is definitely false.
        if is_topic_file_valid(pkg_info, topic) is False:
            return False

        return True

    def is_enabled(self):
        return self.view.match_selector(0, "text.hyperhelp.help")


###----------------------------------------------------------------------------
