import sublime

import collections

# Package paths are always portrayed as a unix path
import posixpath as path


###----------------------------------------------------------------------------


HelpData = collections.namedtuple("HelpData",
    ["package", "description", "index", "doc_root", "topics", "toc"])


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


###----------------------------------------------------------------------------
