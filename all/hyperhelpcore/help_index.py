import sublime
import sublime_plugin

# Inside packages, paths are always posix regardless of the platform in use.
import posixpath as path
from collections import OrderedDict
import os
import re
import codecs

from .common import log, load_resource
from .data import HelpData
from .index_validator import validate_index


###----------------------------------------------------------------------------


_url_prefix_re = re.compile(r'^https?://')


###----------------------------------------------------------------------------


def _import_topics(package, topics, aliases, help_topic_dict, caption_tpl,
                   external=False):
    """
    Parse out a dictionary of help topics from the help index and store all
    topics into the topic dictionary passed in. During the parsing, the
    contents are validated.

    When def_captions is True, topics that don't have a caption use the document
    title as the caption by default.
    """
    def _make_caption(topic, source):
        return caption_tpl.format(topic=topic, source=source, package=package)

    for help_source in help_topic_dict:
        topic_list = help_topic_dict[help_source]

        # Don't include topics from invalid externals.
        if (external
            and not _url_prefix_re.match(help_source)
            and not help_source.startswith("Packages/")):
                log("Discarding invalid external '%s' in %s",
                    help_source, package)
                continue

        default_caption = topic_list[0] if external else None

        # Skip the first entry since it's the title of the help source
        for topic_entry in topic_list[1:]:
            name = topic_entry.get("topic")
            caption = topic_entry.get("caption", None)
            alias_list = topic_entry.get("aliases", [])
            if caption is None:
                caption = default_caption or _make_caption(name, help_source)

            # Normalize whitespace that appears in topics so that only a single
            # whitespace character appears wherever there might be two or more
            # in a row.
            # TODO: This could be a lot cleaner
            name = " ".join(name.casefold().split())
            if name in topics:
                log("Skipping duplicate topic '%s' in %s:%s",
                    name, package, help_source)
            elif name in aliases:
                log("Topic %s is already an alias in %s:%s",
                    name, package, help_source)
            else:
                topics[name] = {
                    "topic": name,
                    "caption": caption,
                    "file": help_source
                }

            for new_name in [" ".join(name.casefold().split()) for name in alias_list]:
                if new_name in topics:
                    log("Alias '%s' is already a topic in %s:%s",
                        new_name, package, help_source)
                elif new_name in aliases:
                    log("Skipping duplicate alias '%s' in %s:%s",
                        new_name, package, help_source)
                else:
                    aliases[new_name] = name

        # All help sources should be in the topic list so you can jump to a
        # file by name. The help file name is the default.
        name = help_source.casefold()
        if name not in topics:
            topics[name] = {
                "topic": name,
                "caption": topic_list[0],
                "file": help_source
            }

    return topics


def _merge_externals(package, externals, topics, package_files, urls):
    """
    Merge the externals into the topic list provided. This ensures that there
    are no duplicate topics during the merge (discarding the external) while
    also splitting the externals into package file specifications and urls.
    """
    for topic, entry in externals.items():
        if topic in topics:
            log("Discarding duplicate external topic '%s' in %s:%s",
                topic, package, entry["file"])
            continue

        file = entry["file"]
        file_list = urls if _url_prefix_re.match(file) else package_files
        if file not in file_list:
            file_list.append(file)

        topics[topic] = entry


def _get_file_metadata(help_topic_dict):
    """
    Parse a dictionary of help topics from the help index and return back an
    ordered dictionary associating help file names with their titles.

    Assumes the help dictionary has already been validated.
    """
    retVal = OrderedDict()
    for file in sorted(help_topic_dict.keys()):
        retVal[file] = help_topic_dict[file][0]

    return retVal


def _get_toc_metadata(help_toc_list, topics, aliases, package):
    """
    Given the table of contents key from the help index and the complete list of
    known topics, return back a table of contents. This will extrapolate a list
    even if the incoming list is empty or non-existant.
    """
    if not help_toc_list:
        return [topics.get(topic) for topic in sorted(topics.keys())]

    def lookup_topic_entry(entry):
        """
        Expand a toc entry from the index into a full topic object.
        """
        if isinstance(entry, str):
            # A string looks up a topic directly; this goes through the alias
            # list if it has to.
            topic = aliases.get(entry, entry)
            return topic, topics.get(topic, None)

        # Use the caption for the topic being referenced if not overridden.
        topic = " ".join(entry["topic"].casefold().split())
        alias = aliases.get(topic, None)
        base_obj = topics.get(alias or topic, None)
        if base_obj is None:
            return topic, None

        entry["file"] = base_obj["file"]
        entry["caption"] = entry.get("caption", base_obj["caption"])

        return topic, entry

    def expand_topic_list(item_list):
        """
        Expand an array of help topics that make up part of a table of contents
        into an array of full topic objects recursively.
        """
        retVal = list()

        for item in item_list:
            topic, info = lookup_topic_entry(item)
            if info is None:
                log("TOC for '%s' is missing topic '%s'; skipping", package, topic)
                continue

            child_topics = info.get("children", None)
            if child_topics:
                info["children"] = expand_topic_list(child_topics)

            retVal.append(info)

        return retVal

    return expand_topic_list(help_toc_list)


def _load_help_index(index_res):
    """
    Given a package name and the resource filename of the hyperhelp json file,
    load the help index and return it. The return value is None on failure or
    HelpData on success.
    """
    if not index_res.casefold().startswith("packages/"):
        return log("Index source is not in a package: %s", index_res)

    content = load_resource(index_res)

    if content is None:
        return log("Unable to load index information from '%s'", index_res)

    raw_dict = validate_index(content, index_res)
    if raw_dict is None:
        return None

    containing_pkg = path.split(index_res)[0].split("/")[1]

    # Top level index keys
    package = raw_dict.pop("package", None)
    description = raw_dict.pop("description", "Help for %s" % package)
    doc_root = raw_dict.pop("doc_root", None)
    help_files = raw_dict.pop("help_files", dict())
    help_toc = raw_dict.pop("help_contents", None)
    externals = raw_dict.pop("externals", None)
    caption_tpl = raw_dict.pop("default_caption",
                                    "Topic {topic} in help source {source}")

    # Warn if the dictionary has too many keys
    for key in raw_dict.keys():
        log("Ignoring unknown key '%s' in index file %s", key, package)

    # If there is no document root, set it from the index resource; otherwise
    # ensure that it's normalized to appear in the appropriate package.
    if not doc_root:
        doc_root = path.split(index_res[len("Packages/"):])[0]
    else:
        doc_root = path.normpath("%s/%s" % (containing_pkg, doc_root))

    # Gather the unique list of topics.
    topic_list = dict()
    alias_list = dict()
    _import_topics(package, topic_list, alias_list, help_files, caption_tpl)

    externals_list = dict()
    package_files = list()
    urls = list()
    if externals is not None:
        _import_topics(package, externals_list, alias_list, externals, caption_tpl, external=True)
        _merge_externals(package, externals_list, topic_list, package_files, urls)

    # Everything has succeeded.
    return HelpData(package, index_res, description, doc_root,
        topic_list, alias_list,
        _get_file_metadata(help_files), package_files, urls,
        _get_toc_metadata(help_toc, topic_list, alias_list, package))


def _is_canonical_pkg_idx(pkg_idx):
    """
    Given a loaded package index, return a determination as to whether it is
    the canonical help for that package or not, which is determined by it being
    present in its own package.
    """
    containing_pkg = path.split(pkg_idx.index_file)[0].split("/")[1]
    return containing_pkg == pkg_idx.package


def _resolve_index_conflict(existing_idx, new_idx):
    """
    Takes two loaded index files that are for the same package and selects one
    to use, which is returned back. The one selected is determined based on the
    load order of the indexes and user settings.

    The return may be None to indicate that neither package should be used.
    """
    existing_canon = _is_canonical_pkg_idx(existing_idx)
    new_canon = _is_canonical_pkg_idx(new_idx)

    log("Warning: Multiple indexes found for package '%s'", new_idx.package)
    log("    %s", existing_idx.index_file)
    log("    %s", new_idx.index_file)

    # When only one of the two packages is canonical, that is the one to use.
    if existing_canon != new_canon:
        if existing_canon:
            log("Warning: Ignoring non-canonical index (%s)", new_idx.index_file)
            return existing_idx

        log("Warning: Using canonical index (%s)", new_idx.index_file)
        return new_idx

    # The canon of both indexes is identical. If neither is canon, always use
    # the most recently loaded one (in package load order), just as result
    # Sublime resources would.
    if existing_canon == False:
        log("Warning: Selecting new index (%s)", new_idx.index_file)
        return new_idx

    # Both are canon, which is not good. This is an error, and we will return
    # None to signal that.
    log("Error: Multiple indexes for '%s' are canonical", new_idx.package)
    return None


def _filter_index(resources, name_filter):
    """
    Filter a list of package index resources so that only indexes contained in
    the package(s) named are returned. When the filter is empty, the entire
    resource list is returned untouched. The filter can be a single package
    name or a list of packages.
    """
    if not name_filter:
        return resources

    if not isinstance(name_filter, list):
        name_filter = [name_filter]

    retVal = []
    for index_file in resources:
        path_parts = path.split(index_file)[0].split("/")
        if path_parts[0] == "Packages" and path_parts[1] in name_filter:
            retVal.append(index_file)

    return retVal


def _scan_help_packages(help_list=None, name_filter=None):
    """
    Scan for packages with a help index and load them. If a help list is
    provided, only the help for packages not already in the list will be
    loaded.
    """
    help_list = dict() if help_list is None else help_list

    # Find all of the index file resources and the list of those that are
    # currently loaded in the provided help list (if any).
    indexes = _filter_index(sublime.find_resources("hyperhelp.json"), name_filter)
    loaded = [help_list[pkg].index_file for pkg in help_list.keys()]

    # The list of packages that are considered broken because they have at
    # least two canonical help indexes dedicated to them.
    broken = []

    # Load all of the indexes that aren't already loaded.
    for index_file in [idx for idx in indexes if idx not in loaded]:
        new_idx = _load_help_index(index_file)
        if new_idx is not None:
            # If this package index is broken, ignore it completely
            if new_idx.package in broken:
                log("Error: Ignoring index for '%s' (%s)", new_idx.package,
                    new_idx.index_file)
                continue

            # If an index already exists for this package, we need to determine
            # which one to use.
            existing_idx = help_list.get(new_idx.package, None)
            if existing_idx is not None:
                # Returns None if both are canonical index files.
                new_idx = _resolve_index_conflict(existing_idx, new_idx)
                if new_idx is None:
                    del help_list[existing_idx.package]
                    broken.append(existing_idx.package)
                    continue

            help_list[new_idx.package] = new_idx

    return help_list


###----------------------------------------------------------------------------
