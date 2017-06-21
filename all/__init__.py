###----------------------------------------------------------------------------

__version_tuple = (1, 0, 0)
__version__ = ".".join([str(num) for num in __version_tuple])


# These are exposed to Sublime to implement the core of the help system.
from .help import HyperHelpCommand, HyperHelpNavigateCommand
from .help import HyperHelpListener


# These are exposed to packages that may want to interface with the hyperhelp
# core for use in their own packages.
from .operations import package_help_scan


###----------------------------------------------------------------------------


def version():
    """
    Get the currently installed version of hyperhelp as a tuple.
    """
    return __version_tuple


###----------------------------------------------------------------------------
