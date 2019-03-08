### ---------------------------------------------------------------------------


from .startup import initialize

__version_tuple = (0, 0, 2)
__version__ = ".".join([str(num) for num in __version_tuple])


### ---------------------------------------------------------------------------


__all__ = [
    "common",
    "core",
    "data",
    "help",
    "initialize",
    "version"
    "view",
]


### ---------------------------------------------------------------------------


def version():
    """
    Get the version of the installed dependency package as a tuple. This is
    used during the bootstrap check to see if the version of the dependency has
    changed.
    """
    return __version_tuple


### ---------------------------------------------------------------------------