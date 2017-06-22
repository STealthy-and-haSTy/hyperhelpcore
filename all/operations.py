import sublime

import collections
import re
import webbrowser

# Package paths are always portrayed as a unix path
import posixpath as path

from .output_view import find_view, output_to_view


###----------------------------------------------------------------------------


HelpData = collections.namedtuple("HelpData",
    ["package", "description", "index", "doc_root", "topics", "toc"])


_url_re = re.compile("^(https?|file)://")

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

    # Extract all top level dictionary keys that are not considered to be a
    # help file.
    #
    # TODO: Validate children in the TOC
    description = raw_dict.pop("__description", "No description available")
    doc_root = raw_dict.pop("__root", None)
    toc = raw_dict.pop("__toc", None)

    if doc_root is None:
        doc_root = path.split(index_file)[0]
    else:
        doc_root = path.normpath("Packages/%s/%s" % (package, doc_root))

    topics = dict()

    for help_file in raw_dict:
        topic_list = raw_dict[help_file]

        if isinstance(topic_list, (bool, str)):
            topic_list = [topic_list]

        for topic_entry in topic_list:
            topic, topic_entry = _make_help_dict(topic_entry, help_file)
            if topic is None:
                return _log("Entry missing topic in package %s: %s",
                           package, str(topic_entry))

            topics[topic] = topic_entry

    if toc is None:
        toc = [topics.get(topic) for topic in sorted(topics.keys())]

    return HelpData(package, description, index_file, doc_root, topics, toc)


###----------------------------------------------------------------------------
### Public API
###----------------------------------------------------------------------------


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

    The new/modified dictionary is returned, and will have a `__scanned` key to
    tell you that a scan was performed.
    """
    help_list = dict() if help_list is None else help_list
    for index_file in sublime.find_resources("hyperhelp.json"):
        pkg_name = path.split(index_file)[0].split("/")[1]
        if pkg_name not in help_list:
            result = _load_index(pkg_name, index_file)
            if result is not None:
                help_list[result.package] = result

    help_list["__scanned"] = True
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
        result = _load_index(pkg_info.package, pkg_info.index)
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
        view.settings().set("_hh_file", help_file)
        view.settings().set("_hh_package", pkg_info.package)
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
        log("No help topic visible to reload")
        return False

    package = view.settings().get("_hh_package", None)
    file = view.settings().get("_hh_file", None)
    pkg_info = help_list.get(package, None)

    if pkg_info is not None and file is not None:
        view.settings().set("_hh_file", "_reload")
        display_help(pkg_info, file)
        return True

    log("Unable to reload current help topic")
    return False


def show_topic(pkg_info, topic):
    """
    Using the help index data provided, display the given help topic by looking
    up the appropriate help file, loading and displaying it, and then focusing
    the cursor on the topic target in the file.

    This can also show a topic that represents a URL or a file contained in a
    package by executing the appropriate command.

    The return value is a boolean which indicates if the topic was displayed or
    not.
    """
    help_file = pkg_info.topics.get(topic, {}).get("file", None)
    if help_file is None:
        log("Unknown help topic '%s'", topic, status=True)
        return False

    if _url_re.match(help_file):
        webbrowser.open_new_tab(help_file)
        return True

    if help_file.startswith("Packages/"):
        help_file = help_file.replace("Packages/", "${packages}/")
        window = sublime.active_window()
        window.run_command("open_file", {"file": help_file})
        return True

    help_view = display_help(pkg_info, help_file)
    if help_view is None:
        log("Unable to load help file '%s'", help_file, status=True)
        return False

    for pos in help_view.find_by_selector('meta.link-target'):
        target = help_view.substr(pos)
        if target == topic:
            focus_on(help_view, pos)
            return True

    log("Unable to find topic '%s' in help file '%s'", topic, help_file,
        status=True)
    return False


###----------------------------------------------------------------------------
