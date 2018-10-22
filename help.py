import sublime
import sublime_plugin

import re
import time

import hyperhelp.core

from .view import find_help_view, update_help_view
from .common import log, hh_syntax, current_help_file, current_help_package
from .common import load_resource
from .data import HeaderData, HistoryData


###----------------------------------------------------------------------------


_header_prefix_re = re.compile(r'^%hyperhelp(\b|$)')
_header_keypair_re = re.compile(r'\b([a-z]+)\b="([^"]*)"')


###----------------------------------------------------------------------------


def _resource_for_help(pkg_info, help_file):
    """
    Get the resource name that references the help file in the given help
    package. The help file should be relative to the document root of the
    package.
    """
    return "Packages/%s/%s" % (pkg_info.doc_root, help_file)


def _load_help_file(pkg_info, help_file):
    """
    Load the contents of a help file contained in the provided help package.
    The help file should be relative to the document root of the package.

    Returns None if the help file cannot be loaded.
    """
    return load_resource(_resource_for_help(pkg_info, help_file))


def _update_help_history(view, append=False, selection=None):
    """
    Update the help history for the provided view by either updating the
    contents of the current history entry or adding a new entry to the end of
    the history list.

    When appending a new history entry, any history after the current position
    in the list is truncated away.

    The selection used to capture the cursor is the first selection in the
    view unless a selection region is provided.
    """
    if view is None:
        return

    selection = view.sel()[0] if selection is None else selection
    settings = view.settings()

    hist_pos = settings.get("_hh_hist_pos", 0)
    hist_info = settings.get("_hh_hist", [])

    if append:
        # Truncate all history after this point; new timeline branches out.
        if hist_pos != len(hist_info) - 1:
            hist_info = hist_info[:hist_pos + 1]

        # Should probably truncate in the other direction to keep history in
        # check.
        hist_pos += 1

    history = HistoryData(current_help_package(view),
                          current_help_file(view),
                          view.viewport_position(),
                          (selection.a, selection.b))

    if hist_pos >= len(hist_info):
        hist_info.append(history)
    else:
        hist_info[hist_pos] = history

    settings.set("_hh_hist_pos", hist_pos)
    settings.set("_hh_hist", hist_info)


def _display_help_file(pkg_info, help_file):
    """
    Load and display the help file contained in the provided help package. The
    help file should be relative to the document root of the package.

    The help will be displayed in the help view of the current window, which
    will be created if it does not exist.

    Does nothing if the help view is already displaying this file.

    Returns None if the help file could not be found/loaded or the help view
    on success.
    """
    view = find_help_view()
    window = view.window() if view is not None else sublime.active_window()

    if view is not None:
        window.focus_view(view)

        current_pkg = current_help_package(view)
        current_file = current_help_file(view)

        if help_file == current_file and pkg_info.package == current_pkg:
            return view

    help_text = _load_help_file(pkg_info, help_file)
    if help_text is not None:
        view = update_help_view(help_text, pkg_info.package, help_file,
                                hh_syntax("HyperHelp.sublime-syntax"))

        # if there is no history yet, add one selection the start of the file.
        if not view.settings().has("_hh_hist_pos"):
            _update_help_history(view, selection=sublime.Region(0))

        _enable_post_processing(view, True)
        _post_process_comments(view)
        _post_process_header(view)
        _post_process_links(view)
        view.run_command("hyperhelp_internal_capture_anchors")
        _enable_post_processing(view, False)

        return view

    return log("Unable to find help file '%s'", help_file, status=True)


def _enable_post_processing(help_view, enable):
    """
    Enable or disable post processing on the provided help view, which controls
    whether or not the file can be edited and whether various processing
    commands are enabled.
    """
    help_view.set_read_only(not enable);
    help_view.settings().set("_hh_processing_enabled", enable)


def _reload_help_file(help_list, help_view):
    """
    Reload the help file currently being displayed in the given view to pick
    up changes made since it was displayed. The information on the package and
    help file should be contained in the provided help list.

    Returns True if the file was reloaded successfully or False if not.
    """
    if help_view is None:
        log("No help topic is visible; cannot reload")
        return False

    package = current_help_package(help_view)
    file = current_help_file(help_view)
    pkg_info = help_list.get(package, None)

    if pkg_info is not None and file is not None:
        # Remove the file setting so the view will reload; put it back if the
        # reload fails so we can still track what the file used to be.
        settings = help_view.settings()
        settings.set("_hh_file", "")
        if _display_help_file(pkg_info, file) is None:
            settings.set("_hh_file", file)
            return false

        return True

    log("Unable to reload the current help topic")
    return False


def _parse_header(help_file, header_line):
    """
    Given the first line of a help file, check to see if it looks like a help
    source file, and if so parse the header and return the parsed values back.
    """
    if not _header_prefix_re.match(header_line):
        return None

    title = "No Title Provided"
    date = 0.0

    for match in re.findall(_header_keypair_re, header_line):
        if match[0] == "title":
            title = match[1]
        elif match[0] == "date":
            try:
                date = time.mktime(time.strptime(match[1], "%Y-%m-%d"))
            except:
                date = 0.0
                log("Ignoring invalid file date '%s' in '%s'",
                    match[1], help_file)
        else:
            log("Ignoring unknown header key '%s' in '%s'",
                match[1], help_file)

    return HeaderData(help_file, title, date)


def _post_process_comments(help_view):
    """
    Strip away from the provided help all comments that may exist in the
    buffer. This should happen prior to all other post processing since
    it will change the locations of items in the buffer.
    """
    for region in reversed(help_view.find_by_selector("comment")):
        help_view.sel().clear()
        help_view.sel().add(region)
        help_view.run_command("left_delete")


def _post_process_header(help_view):
    """
    Check if the help file contains a formatted header line. If it does it is
    replaced with a version that more explicitly describes the help. This
    includes a link to the top level of the help file itself.
    """
    help_file = current_help_file(help_view)
    first_line = help_view.substr(help_view.full_line(0))

    header = _parse_header(help_file, first_line)
    if header is None:
        return

    _hdr_width = 80
    _time_fmt = help_view.settings().get("hyperhelp_date_format", "%x")

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

    help_view.sel().clear()
    help_view.sel().add(help_view.full_line(0))
    help_view.run_command("insert", {"characters": header_line})


def _post_process_links(help_view):
    """
    Find all of the links in the provided help view and underline them.
    """
    pkg_name = current_help_package(help_view)
    pkg_info = hyperhelp.core.help_index_list().get(pkg_name, None)

    active = []
    broken = []

    regions = help_view.find_by_selector("meta.link")
    for region in help_view.find_by_selector("meta.link"):
        topic = help_view.substr(region)

        if hyperhelp.core.lookup_help_topic(pkg_info, topic) is not None:
            active.append(region)
        else:
            broken.append(region)

    help_view.add_regions("_hh_links_active", active, "storage",
        flags=sublime.DRAW_SOLID_UNDERLINE | sublime.PERSISTENT |
              sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

    help_view.add_regions("_hh_links_broken", broken, "comment",
        flags=sublime.DRAW_STIPPLED_UNDERLINE | sublime.PERSISTENT |
              sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)


###----------------------------------------------------------------------------
