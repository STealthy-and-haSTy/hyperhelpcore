###----------------------------------------------------------------------------

__version_tuple = (1, 0, 0)
__version__ = ".".join([str(num) for num in __version_tuple])


# These are exposed to Sublime to implement the core of the help system.
from .help import HyperHelpCommand, HyperHelpNavigateCommand
from .help import HyperHelpListener


# These functions represent the API that is exposed to external packages that
# may want/need to get at some of the internals of hyperhelp.
from .operations import scan_packages, reload_package
from .operations import help_view, focus_on, display_help, reload_help
from .operations import show_topic


###----------------------------------------------------------------------------


def version():
    """
    Get the currently installed version of hyperhelp as a tuple.
    """
    return __version_tuple


###----------------------------------------------------------------------------
