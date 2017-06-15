import sublime

import os
import collections


###----------------------------------------------------------------------------


HelpData = collections.namedtuple("HelpData", ["package", "topics", "toc"])


###----------------------------------------------------------------------------


def log(message, *args, status=False, dialog=False):
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


def load_index_json(package, index_file):
    """
    Takes a package name and its associated hyperhelp.json index resource name
    and loads it.

    On success, the return value is a HelpData tuple containing the loaded
    information.
    """

    try:
        log("Loading help index for package %s", package)
        json = sublime.load_resource(index_file)
        raw_dict = sublime.decode_value(json)

    except:
        return log("Unable to load help index from '%s'", index_file)

    # Extract all top level dictionary keys that are not considered to be a
    # help file.
    #
    # TODO: Validate children in the TOC
    toc = raw_dict.pop("__toc", None)

    topics = dict()

    for help_file in raw_dict:
        topic_list = raw_dict[help_file]

        if isinstance(topic_list, (bool, str)):
            topic_list = [topic_list]

        for topic_entry in topic_list:
            topic, topic_entry = _make_help_dict(topic_entry, help_file)
            if topic is None:
                return log("Entry missing topic in package %s: %s",
                           package, str(topic_entry))

            topics[topic] = topic_entry

    if toc is None:
        toc = [topics.get(topic) for topic in sorted(topics.keys())]

    return HelpData(package, topics, toc)


###----------------------------------------------------------------------------


def package_help_scan(help_list):
    """
    Update the provided help_list by finding and loading the hyperhelp.json
    index file for any package not already contained in the help list.

    This scans only for user installed packages under the theory that a shipped
    package is unlikely to contain a help index.
    """
    for index_file in sublime.find_resources("hyperhelp.json"):
        pkg_name = os.path.split(index_file)[0].split("/")[1]

        if pkg_name not in help_list:
            result = load_index_json(pkg_name, index_file)
            if result is not None:
                help_list[result.package] = result

    help_list["__scanned"] = True



###----------------------------------------------------------------------------
