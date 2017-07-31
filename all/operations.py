import sublime

import collections
import re
import time
import webbrowser

# Package paths are always portrayed as a unix path
import posixpath as path

from .output_view import find_view, output_to_view


###----------------------------------------------------------------------------


HelpData = collections.namedtuple("HelpData",
    ["package", "description", "index_file", "doc_root", "topics",
     "files", "package_files", "urls", "toc"])

HeaderData = collections.namedtuple("HeaderData",
    ["file", "title", "date"])

HistoryData = collections.namedtuple("HistoryData",
    ["package", "file", "viewport", "caret"])

_header_prefix_re = re.compile(r'^%hyperhelp(\b|$)')
_header_keypair_re = re.compile(r'\b([a-z]+)\b="([^"]*)"')


###----------------------------------------------------------------------------


def _log(message, *args, status=False, dialog=False):
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


def _make_help_dict(topic_data, help_file):
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


def _process_topic_dict(package, topics, help_topic_dict):
    """
    Takes a dictionary which contains keys that are "files" and values that
    are topics, and expands them out into the topic list provided.
    """
    for help_file in help_topic_dict:
        topic_list = help_topic_dict[help_file]

        if isinstance(topic_list, (bool, str)):
            topic_list = [topic_list]

        for topic_entry in topic_list:
            topic, topic_entry = _make_help_dict(topic_entry, help_file)
            if topic is None:
                return _log("Entry missing topic in package %s: %s",
                           package, str(topic_entry))

            if topic in topics:
                _log("Package %s contains duplicate topic '%s'", package, topic)
            else:
                topics[topic] = topic_entry


def _validate_toc(package, toc, topics):
    """
    Perform a recursive check to ensure that all of the topics in the provided
    table of contents actually exist in the help file. Any that don't generate
    a warning to the console but are otherwise left alone.
    """
    for entry in toc:
        topic = entry["topic"]
        if topic not in topics:
            _log("TOC for package %s contains missing topic %s", package, topic)

        children = entry.get("children", None)
        if children is not None:
            _validate_toc(package, children, topics)


def _load_index(package, index_file):
    """
    Takes a package name and its associated hyperhelp.json index resource name
    and loads it. Returns None on failure or a HelpData tuple for the loaded
    help information on success.
    """
    try:
        _log("Loading help index for package %s", package)
        json = sublime.load_resource(index_file)
        raw_dict = sublime.decode_value(json)

    except:
        return _log("Unable to load help index from '%s'", index_file)

    # Extract all known top level dictionary keys from the help index
    description = raw_dict.pop("description", "No description available")
    doc_root = raw_dict.pop("doc_root", None)
    toc = raw_dict.pop("toc", None)
    help_files = raw_dict.pop("help_files", dict())
    package_files = raw_dict.pop("package_files", dict())
    urls = raw_dict.pop("urls", dict())

    # Warn about unknown keys still in the dictionary; they are harmless, but
    # probably the author did something dodgy.
    for key in raw_dict.keys():
        _log("Unknown key '%s' in help index for package '%s'", key, package)

    if doc_root is None:
        doc_root = path.split(index_file)[0]
    else:
        doc_root = path.normpath("Packages/%s/%s" % (package, doc_root))

    # Pull in all the topics.
    topics = dict()
    _process_topic_dict(package, topics, help_files)
    _process_topic_dict(package, topics, package_files)
    _process_topic_dict(package, topics, urls)

    if toc is None:
        toc = [topics.get(topic) for topic in sorted(topics.keys())]
    else:
        _validate_toc(package, toc, topics)

    return HelpData(package, description, index_file, doc_root, topics,
                    sorted(help_files.keys()),
                    sorted(package_files.keys()),
                    list(urls.keys()),
                    toc)


def _postprocess_header(view):
    """
    Perform post processing on a loaded help view by transforming a potential
    %hyperhelp header line into a more complete header line, including the
    name of the file, it's title and its edit date.
    """
    help_file = view.settings().get("_hh_file")
    first_line = view.substr(view.full_line(0))
    header = parse_header(help_file, first_line)
    if header is None:
        return

    _hdr_width = 80
    _time_fmt = view.settings().get("hyperhelp_date_format", "%x")

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

    view.sel().clear()
    view.sel().add(view.full_line(0))
    view.set_read_only(False)
    view.run_command("insert", {"characters": header_line})
    view.set_read_only(True)


def _postprocess_help(view):
    """
    Perform post processing on a loaded help view to do any transformations
    needed on the help content before control is handed back to the user to
    interact with it.
    """
    _postprocess_header(view)

    # Underlink all links.
    # TODO: Populate via a setting only?
    view.add_regions("_hh_link", view.find_by_selector("meta.link"), "storage",
        flags=sublime.DRAW_SOLID_UNDERLINE|sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE)


def _update_history(view, append=False, selection=None):
    """
    Update the history for the current view by either updating the contents of
    the current history entry (append is False) or adding a new entry (append
    is True). When appending a new history entry, any history after the
    entry currently being displayed is truncated away.

    In either case, the selection used is either the one passed in or the
    first selection in the buffer if the passed selection is None, and the
    view must have the settings that indicate what package and help file are
    currently being viewed.

    When append is False and the view has no history information yet, a new
    history is added to the view.
    """
    if view is None:
        return

    selection = view.sel()[0] if selection is None else selection
    settings = view.settings()

    hist_pos = settings.get("_hh_hist_pos", 0)
    hist_info = settings.get("_hh_history", [])

    if append:
        # Truncate history after this point; new timeline branches here
        if hist_pos != len(hist_info) - 1:
            hist_info = hist_info[:hist_pos + 1]

        # TODO: This should maybe also do a similar truncation with a slice in
        # the other direction to keep the history from getting arbitrarily
        # long.
        hist_pos += 1

    history = HistoryData(settings.get("_hh_package"),
                          settings.get("_hh_file"),
                          view.viewport_position(),
                          (selection.a, selection.b))

    if hist_pos >= len(hist_info):
        hist_info.append(history)
    else:
        hist_info[hist_pos] = history

    settings.set("_hh_hist_pos", hist_pos)
    settings.set("_hh_history", hist_info)


###----------------------------------------------------------------------------
### Public API
###----------------------------------------------------------------------------


def help_index_list(reload=False, package=None):
    """
    Return the global help list. This will demand load the help index only
    when it is accessed, and can also force a reload of help indexes, possibly
    of only a particular package, if requested.
    """
    initial_load = False
    if not hasattr(help_index_list, "index"):
        initial_load = True
        help_index_list.index = scan_packages()

    if reload and not initial_load:
        help_index_list.index = reload_package(help_index_list.index, package)

    return help_index_list.index


def focus_on(view, position):
    """
    Focus the given help view on the provided position to ensure that is is
    visible. This alters the selection to the given position.

    If position is a point, the view is focused on that point and the cursor is
    placed there. If it is a Region, the region is selected and the cursor is
    left at the beginning of the region instead of at the end.
    """
    if isinstance(position, int):
        position = sublime.Region(position, position)
    else:
        position = sublime.Region(position.end(), position.begin())

    view.show_at_center(position)
    view.sel().clear()
    view.sel().add(position)

    # Hack to make the view update properly. See:
    #    https://github.com/SublimeTextIssues/Core/issues/485
    view.add_regions("_hh_rk", [], "", "", sublime.HIDDEN)
    view.erase_regions("_hh_rk")


def scan_packages(help_list=None):
    """
    Find all packages with a help index and load it, returning a dictionary of
    the packages found. If a partial help dictionary is passed, only packages
    it does not contain will be added.
    """
    help_list = dict() if help_list is None else help_list
    for index_file in sublime.find_resources("hyperhelp.json"):
        pkg_name = path.split(index_file)[0].split("/")[1]
        if pkg_name not in help_list:
            result = _load_index(pkg_name, index_file)
            if result is not None:
                help_list[result.package] = result

    return help_list


def reload_package(help_list, package):
    """
    Find the package provided in the list of previously loaded help and reload
    the help index file, updating the provided help list to represent the new
    information.

    If no package name is provided, the help list given is ignored and this is
    the same as invoking scan_packages() with no help list provided.

    The return value is the new or updated help list.
    """
    if package is None:
        _log("Rescanning all help index files")
        return scan_packages()

    pkg_info = help_list.get(package, None)
    if pkg_info is None:
        _log("Package '%s' not previously loaded; cannot reload", package)
    else:
        _log("Reloading help index for package '%s'", package)
        result = _load_index(pkg_info.package, pkg_info.index_file)
        if result is not None:
            help_list[result.package] = result

    return help_list


def load_help(pkg_info, help_file):
    """
    Load and return the contents of the help file with the given name from the
    provided package. The help file name should be relative to the set document
    root for the package given.

    Returns the contents of the help file or None.
    """
    try:
        return sublime.load_resource("%s/%s" % (pkg_info.doc_root, help_file))
    except:
        pass

    return None


def help_view(window=None):
    """
    Find and return the help view for the provided window. If no window is
    provided, the currently active window is checked instead.

    The return value is the view on success or None if there is currently no
    help view in the window.
    """
    window = window if window is not None else sublime.active_window()
    view = find_view(window, "HyperHelp")
    if view is not None:
        settings = view.settings()
        if settings.has("_hh_package") and settings.has("_hh_file"):
            return view

    return None


def parse_header(help_file, header_line):
    """
    Given the name of a help file and its first line, return back a HeaderData
    that provides the information from the header.

    The return value is None if the line is not a valid file header.
    """
    if not _header_prefix_re.match(header_line):
        return None

    result = re.findall(_header_keypair_re, header_line)

    title = "No Title provided"
    date = 0.0
    for match in result:
        if match[0] == "title":
            title = match[1]
        elif match[0] == "date":
            try:
                date = time.mktime(time.strptime(match[1], "%Y-%m-%d"))
            except:
                _log("Ignoring invalid file date '%s'", match[1])
                date = 0.0
        else:
            _log("Ignoring header key '%s' in '%s'", match[0], help_file)

    return HeaderData(help_file, title, date)


def display_help(pkg_info, help_file):
    """
    Load and display the help file with the given name from the provided
    package. The help file name should be relative to the set document
    root for the package given.

    The help is displayed in a help view for the current window, which
    will be given the focus if it does not already have it. If there is no
    such view yet, one is created; otherwise the existing help view is used.

    When a help view exists and is already displaying the given file, nothing
    happens.

    Returns None if the help file could not be found or the view holding the
    help on success.
    """
    view = help_view()
    window = view.window() if view is not None else sublime.active_window()

    if view is not None:
        window.focus_view(view)

        current_pkg = view.settings().get("_hh_package", None)
        current_file = view.settings().get("_hh_file", None)

        if help_file == current_file and pkg_info.package == current_pkg:
            return view

    help_text = load_help(pkg_info, help_file)
    if help_text is not None:
        view = output_to_view(window,
                              "HyperHelp",
                              help_text,
                              syntax="Packages/hyperhelp/all/Help.sublime-syntax")
        settings = view.settings()
        settings.set("_hh_file", help_file)
        settings.set("_hh_package", pkg_info.package)

        # For a newly created help view, Create an initial history entry. The
        # saved selection sets the cursor to the start of the file.
        if not settings.has("_hh_hist_pos"):
            _update_history(view, append=False, selection=sublime.Region(0, 0))

        _postprocess_help(view)
        return view

    return None


def reload_help(help_list):
    """
    Reload the file currently displayed in the help view for the current
    window, if any.

    If there is no help view or the package it is displaying help for is not
    in the list of packages in the provided help list, nothing happens.

    Returns True if the current file was reloaded or False if it was not.
    """
    view = help_view()
    if view is None:
        _log("No help topic visible to reload")
        return False

    package = view.settings().get("_hh_package", None)
    file = view.settings().get("_hh_file", None)
    pkg_info = help_list.get(package, None)

    if pkg_info is not None and file is not None:
        view.settings().set("_hh_file", "_reload")
        display_help(pkg_info, file)
        return True

    _log("Unable to reload current help topic")
    return False


def navigate_history(prev):
    """
    Navigate the current help view through its help topic display history by
    altering the currently set history position by one item in either direction
    and then displaying that topic.

    This updates the history position that the view is displaying but otherwise
    leaves things alone.

    The return value is True if the history position changed or false
    otherwise.
    """
    view = help_view()
    if view is None:
        return False

    history = view.settings().get("_hh_history")
    pos = view.settings().get("_hh_hist_pos")

    if (prev and pos == 0) or (not prev and pos == len(history) - 1):
        _log("Cannnot navigate history; at end of history")
        return False

    pos = (pos - 1) if prev else (pos + 1)
    entry = HistoryData._make(history[pos])

    # Save current position in this history entry, then switch to the new one
    _update_history(view)
    if show_topic(entry.package, entry.file, update_history=False) is not None:
        view.sel().clear()
        view.sel().add(sublime.Region(entry.caret[0], entry.caret[1]))
        view.set_viewport_position(entry.viewport, False)
        view.settings().set("_hh_hist_pos", pos)
        return True

    return False


def show_topic(package, topic, update_history):
    """
    Attempt to display the help for the provided help topic and package. This
    either displays the appropriate part of the given help file, opens a url in
    a browser, or opens the contents of a package file.

    If update_history is true, the history for the help view is updated after
    a successful help navigation to a help file, otherwise the history is left
    untouched. The function acts as if update_history is True if it has to
    create a new help view in order to display a help file.

    The return value is None on error or a string that represents the result of
    the operation.
    """
    pkg_info = help_index_list().get(package, None)
    if pkg_info is None:
        return None

    help_file = pkg_info.topics.get(topic, {}).get("file", None)
    if help_file is None:
        _log("Unknown help topic '%s'", topic, status=True)
        return None

    if help_file in pkg_info.urls:
        webbrowser.open_new_tab(help_file)
        return "url"

    if help_file in pkg_info.package_files:
        help_file = help_file.replace("Packages/", "${packages}/")
        window = sublime.active_window()
        window.run_command("open_file", {"file": help_file})
        return "pkg_file"

    # Update the position in the current help file before navigating away
    if update_history:
        _update_history(help_view())

    existing_view = True if help_view() is not None else False
    view = display_help(pkg_info, help_file)
    if view is None:
        _log("Unable to load help file '%s'", help_file, status=True)
        return None

    found = False
    for pos in view.find_by_selector('meta.link-target'):
        target = view.substr(pos)
        if target == topic:
            focus_on(view, pos)
            found = True

    # Add a new history entry as long as this view previously existed
    if update_history and existing_view:
        _update_history(view, append=True)

    # Warn on topic not found
    if not found:
        _log("Unable to find topic '%s' in help file '%s'", topic, help_file,
             status=True)
    return "file"


###----------------------------------------------------------------------------
