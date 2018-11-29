import sublime
import sublime_plugin

import re
import time

from .view import find_help_view, update_help_view
from .common import log, hh_syntax, current_help_file, current_help_package
from .common import load_resource
from .data import HistoryData


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


def _enable_post_processing(help_view, enable):
    """
    Enable or disable post processing on the provided help view, which controls
    whether or not the file can be edited and whether various post-processing
    commands are enabled.
    """
    help_view.set_read_only(not enable);
    help_view.settings().set("_hh_post_processing", enable)


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
                                hh_syntax("HyperHelp-Help.sublime-syntax"))

        # if there is no history yet, add one selection the start of the file.
        if not view.settings().has("_hh_hist_pos"):
            _update_help_history(view, selection=sublime.Region(0))

        _enable_post_processing(view, True)
        view.run_command("hyperhelp_internal_process_header")
        view.run_command("hyperhelp_internal_process_comments")
        view.run_command("hyperhelp_internal_process_anchors")
        view.run_command("hyperhelp_internal_process_links")
        _enable_post_processing(view, False)

        return view

    return log("Unable to find help file '%s'", help_file, status=True)


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


def _get_link_topic(help_view, link_region):
    """
    Given a help view and information about a link, return back an object that
    provides the package and topic ID that the link references.

    region can be a Region object, in which case the link data is looked up by
    region. It can also be an integer, in which case it represents the index of
    that link, with the first link in the file being numbered as 0.

    None is returned when the information cannot be found.
    """
    topic_data = None
    topics = help_view.settings().get("_hh_links")

    try:
        # If the incoming region is an index, our job is easy.
        if isinstance(link_region, int):
            return topics[link_region]

        for idx, region in enumerate(help_view.get_regions("_hh_links")):
            if region == link_region:
                return topics[idx]
    except:
        pass

    return None


###----------------------------------------------------------------------------
