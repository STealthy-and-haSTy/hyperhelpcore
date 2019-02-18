import sublime

import os
import re
import time
import webbrowser

from urllib.parse import urlparse

from .common import log, hh_syntax
from .view import find_help_view, update_help_view

from .help_index import _load_help_index, _scan_help_packages
from .help import _resource_for_help
from .help import _load_help_file, _display_help_file, _reload_help_file
from .help import HistoryData, _update_help_history
from .data import HeaderData


###----------------------------------------------------------------------------


_header_prefix_re = re.compile(r'^%hyperhelp(\b|$)')
_header_keypair_re = re.compile(r'\b([a-z]+)\b="([^"]*)"')


###----------------------------------------------------------------------------


def load_help_index(index_resource):
    """
    Given an index resource that points to a hyperhelp.json file, load the help
    index and return back a normalized version. Returns None on error.
    """
    return _load_help_index(index_resource)


def load_help_file(pkg_info, help_file):
    """
    Load the contents of a help file contained in the provided help package.
    The help file should be relative to the document root of the package.

    Returns None if the help file cannot be loaded.
    """
    return _load_help_file(pkg_info, help_file)


def help_index_list(reload=False, package=None):
    """
    Obtain or reload the help index information for all packages. This demand
    loads the indexes on first access and can optionally reload all package
    indexes or only a single one, as desired.
    """
    initial_load = False
    if not hasattr(help_index_list, "index"):
        initial_load = True
        help_index_list.index = _scan_help_packages()

    if reload and not initial_load:
        help_index_list.index = reload_help_index(help_index_list.index, package)

    return help_index_list.index


def reload_help_index(help_list, package):
    """
    Reload the help index for the provided package from within the given help
    list, updating the help list to record the new data.

    If no package name is provided, the help list provided is ignored and all
    help indexes are reloaded and returned in a new help list.

    Attempts to reload a package that is not in the given help list has no
    effect.
    """
    if package is None:
        log("Recanning all help index files")
        return _scan_help_packages()

    pkg_info = help_list.get(package, None)
    if pkg_info is None:
        log("Package '%s' was not previously loaded; cannot reload", package)
    else:
        log("Reloading help index for package '%s'", package)

        result = _load_help_index(pkg_info.index_file)
        if result is not None:
            help_list[result.package] = result

            # If the package changed from what it used to be, remove the old
            # one from the list of packages.
            if result.package != package:
                log("Warning: package name in index changed (%s became %s)",
                    package, result.package)
                del help_list[package]

    return help_list


def help_file_resource(pkg_info, help_file):
    """
    Get the resource name that references the help file in the given help
    package. The help file should be relative to the document root of the
    package.
    """
    return _resource_for_help(pkg_info, help_file)


def load_help_file(pkg_info, help_file):
    """
    Load the contents of a help file contained in the provided help package.
    The help file should be relative to the document root of the package.

    Returns None if the help file cannot be loaded.
    """
    return _load_help_file(pkg_info, help_file)


def display_help_file(pkg_info, help_file):
    """
    Load and display the help file contained in the provided help package. The
    heop file should be relative to the document root of the package.

    The help will be displayed in the help view of the current window, which
    will be created if it does not exist.

    Does nothing if the help view is already displaying this file.

    Returns None if the help file could not be found/loaded or the help view
    on success.
    """
    return _display_help_file(pkg_info, help_file)


def reload_help_file(help_list, help_view):
    """
    Reload the help file currently being displayed in the given view to pick
    up changes made since it was displayed. The information on the package and
    help file should be contained in the provided help list.

    Returns True if the file was reloaded successfully or False if not.
    """
    return _reload_help_file(help_list, help_view)


def lookup_help_topic(pkg_info, topic):
    """
    Given a help data tuple or the name of a package, look up the topic and
    return the topic structure if needed.

    This does all manipulations on the incoming topic, such as case folding and
    space replacement.

    Returns the topic structure or None.
    """
    if isinstance(pkg_info, str):
        pkg_info = help_index_list().get(pkg_info, None)

    if pkg_info is not None:
        topic = " ".join(topic.casefold().split())
        alias = pkg_info.help_aliases.get(topic, None)
        return pkg_info.help_topics.get(alias or topic, None)

    return None


def is_topic_normal(pkg_info, topic_dict):
    """
    Given a topic dictionary such as returned by lookup_help_topic(), determine
    if the topic represents a "normal" topic or not.
    """
    return (not is_topic_url(pkg_info, topic_dict) and
            not is_topic_file(pkg_info, topic_dict))


def is_topic_url(pkg_info, topic_dict):
    """
    Given a topic dictionary such as returned by lookup_help_topic(), determine
    if the topic represents a topic that will open a URL or not.
    """
    return topic_dict["file"] in pkg_info.urls


def is_topic_file(pkg_info, topic_dict):
    """
    Given a topic dictionary such as returned by lookup_help_topic(), determine
    if the topic represents a topic that will open a URL or not.
    """
    return topic_dict["file"] in pkg_info.package_files


def is_topic_url_valid(pkg_info, topic_dict):
    """
    Given a topic dictionary such as returned by lookup_help_topic() that
    represents a URL, return an indication as to whether the URL is valid or
    not.

    None is returned if a topic does not represent a URL.
    """
    if is_topic_url(pkg_info, topic_dict):
        try:
            result = urlparse(topic_dict["file"])
            return result.scheme and result.netloc
        except:
            return False

    return None


def is_topic_file_valid(pkg_info, topic_dict):
    """
    Given a topic dictionary such as returned by lookup_help_topic() that
    represents a package file, return an indication as to whether that file
    exists or not as a package resource.

    None is returned if a topic does not represent a package file.
    """
    if is_topic_file(pkg_info, topic_dict):
        file = topic_dict["file"]
        base = os.path.split(file)[1]
        if file not in sublime.find_resources(base):
            return False

        return True

    return None


def show_help_topic(package, topic, history):
    """
    Attempt to display the help for the provided topic in the given package
    (both strings) as appropriate. This will transparently create a new help
    view, open the underlying package file or open the URL as needed.

    If history is True, the history for the help view is updated after a
    successful help navigation to a help file; otherwise the history is left
    untouched. history is implicitly True when this has to create a help view
    for the first time so that history is properly initialized.

    The return value is None on error or a string that represents the kind of
    topic that was navigated to ("file", "pkg_file" or "url")
    """
    pkg_info = help_index_list().get(package, None)
    if pkg_info is None:
        return None

    topic_data = lookup_help_topic(pkg_info, topic)
    if topic_data is None:
        log("Unknown help topic '%s'", topic, status=True)
        return None

    help_file = topic_data["file"]

    if help_file in pkg_info.urls:
        webbrowser.open_new_tab(help_file)
        return "url"

    if help_file in pkg_info.package_files:
        help_file = help_file.replace("Packages/", "${packages}/")
        window = sublime.active_window()
        window.run_command("open_file", {"file": help_file})
        return "pkg_file"

    # Update the current history entry if there is a help view.
    if history:
        _update_help_history(find_help_view())

    existing_view = True if find_help_view() is not None else False
    help_view = display_help_file(pkg_info, help_file)
    if help_view is None:
        log("Unable to load help file '%s'", help_file, status=True)
        return None

    found = False
    anchor_dict = help_view.settings().get("_hh_nav", [])
    idx = anchor_dict.get(topic_data["topic"], -1)
    if idx >= 0:
        anchor_pos = help_view.get_regions("_hh_anchors")[idx]
        help_view.run_command("hyperhelp_focus",
            {
                "position": [anchor_pos.b, anchor_pos.a],
                "at_center": True
            })
        found = True

    # Update history to track the new file, but only if the help view already
    # existed; otherwise its creation set up the default history already.
    if history and existing_view:
        _update_help_history(help_view, append=True)

    if not found:
        log("Unable to find topic '%s' in help file '%s'", topic, help_file,
            status=True)
    return "file"


def navigate_help_history(help_view, prev):
    """
    Navigate through the help history for the provided help view, either going
    forward or backward as appropriate. This will update the current history
    entry before displaying the historic topic.

    If no help view is provided, the current help view is used instead, if any.

    Returns a boolean to tell you if the history position changed or not.
    """
    help_view = help_view or find_help_view()
    if help_view is None:
        return False

    hist_pos = help_view.settings().get("_hh_hist_pos")
    hist_info = help_view.settings().get("_hh_hist")

    if (prev and hist_pos == 0) or (not prev and hist_pos == len(hist_info) - 1):
        log("Cannot navigate %s through history; already at the end",
            "backwards" if prev else "forwards", status=True)
        return False

    hist_pos = (hist_pos - 1) if prev else (hist_pos + 1)
    entry = HistoryData._make(hist_info[hist_pos])

    # Update the current history entry's viewport and caret location
    _update_help_history(help_view)

    # Navigate to the destination file in the history; need to manually set
    # the cursor position
    if show_help_topic(entry.package, entry.file, history=False) is not None:
        help_view.sel().clear()
        help_view.sel().add(sublime.Region(entry.caret[0], entry.caret[1]))
        help_view.set_viewport_position(entry.viewport, False)

        help_view.settings().set("_hh_hist_pos", hist_pos)
        return True

    return False


def jump_help_history(help_view, new_pos):
    """
    Jump to a specific point in the help history for the provided help view.

    If no help view is provided, the current help view is used instead, if any.

    Returns a boolean to tell you if the history position changed or not; it
    may not change if the history index is not valid, for example.
    """
    help_view = help_view or find_help_view()
    if help_view is None:
        return False

    hist_pos = help_view.settings().get("_hh_hist_pos")
    hist_info = help_view.settings().get("_hh_hist")

    if new_pos < 0 or new_pos >= len(hist_info) or new_pos == hist_pos:
        return False

    entry = HistoryData._make(hist_info[new_pos])

    # Update the current history entry's viewport and caret location
    _update_help_history(help_view)

    # Navigate to the destination file in the history; need to manually set
    # the cursor position
    if show_help_topic(entry.package, entry.file, history=False) is not None:
        help_view.sel().clear()
        help_view.sel().add(sublime.Region(entry.caret[0], entry.caret[1]))
        help_view.set_viewport_position(entry.viewport, False)

        help_view.settings().set("_hh_hist_pos", new_pos)
        return True


def clear_help_history(help_view):
    """
    Clear the help history for the provided help file, leaving only the current
    entry in the list as the sole history entry.

    If no help view is provided, the current help view is used instead, if any.

    Returns a boolean to tell you if history changed or not.
    """
    help_view = help_view or find_help_view()
    if help_view is None:
        return False

    hist_pos = help_view.settings().get("_hh_hist_pos")
    hist_info = help_view.settings().get("_hh_hist")

    entry = HistoryData._make(hist_info[hist_pos])

    help_view.settings().set("_hh_hist_pos", 0)
    help_view.settings().set("_hh_hist", [entry])

    return True


def parse_help_header(help_file, header_line):
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
            except Exception as e:
                print(e)
                date = 0.0
                log("Ignoring invalid file date '%s' in '%s'",
                    match[1], help_file)
        else:
            log("Ignoring unknown header key '%s' in '%s'",
                match[1], help_file)

    return HeaderData(help_file, title, date)


def parse_anchor_body(anchor_body):
    """
    Given the body of an anchor, parse it to determine what topic ID it's
    anchored to and what text the anchor uses in the source help file.

    This always returns a 2-tuple, though based on the anchor body in the file
    it may end up thinking that the topic ID and the text are identical.
    """
    c_pos = anchor_body.find(':')
    if c_pos >= 0:
        id_val = anchor_body[:c_pos]
        anchor_body = anchor_body[c_pos+1:]

        id_val = id_val or anchor_body
    else:
        id_val = anchor_body

    return (id_val.casefold().rstrip(), anchor_body.strip())


def parse_link_body(link_body):
    """
    Given the body of a link, parse it to determine what package and topic ID
    the link will navigate to as well as what the visual link text should be.

    This always returns a 3-tuple, though the value of the link text will be
    None if the parse failed. It's possible for the package to be None, in
    which case you can infer what the default package should be.
    """
    parts = link_body.split(':')
    if len(parts) == 1:
        return None, link_body.rstrip(), link_body.rstrip()

    if len(parts) >= 3:
        pkg = parts[0]
        topic = parts[1]
        text = ":".join(parts[2:])
    else:
        return (None, None, None)

    pkg = pkg or None
    topic = topic or text
    return (pkg, topic.strip(), text.strip())


###----------------------------------------------------------------------------
