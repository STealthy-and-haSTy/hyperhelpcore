from collections import OrderedDict, namedtuple


###----------------------------------------------------------------------------


# A representation of the data that was contained in a hyperhelp help document
# header. This is used to construct a more human readable header.
HeaderData = namedtuple("HeaderData", [
    "file", "title", "date"
])

# A representation of a history node that tracks what help topics have been
# viewed and where the viewport was left.
HistoryData = namedtuple("HistoryData", [
    "package", "file", "viewport", "caret"
])

# A representation of all of the help available for a particular package.
#
# This tells us all of the information we need about the help for a package at
# load time so that we don't need to look it up later.
HelpData = namedtuple("HelpData", [
    "package", "index_file", "description", "doc_root", "help_topics",
    "help_aliases", "help_files", "package_files", "urls", "help_toc"
])


###----------------------------------------------------------------------------
