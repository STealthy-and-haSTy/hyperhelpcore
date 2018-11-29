### ---------------------------------------------------------------------------


# When the bootstrapped system package is created or updated, the value of this
# tuple is updated to the version of the dependency that is doing the
# bootstrap.
#
# The bootstrap code looks specifically for this line, so don't modify it.
__core_version_tuple = (0, 0, 0)

__version_tuple = __core_version_tuple
__version__ = ".".join([str(num) for num in __version_tuple])


### ---------------------------------------------------------------------------


def version():
    """
    Get the currently installed version of the bootstrapped version of the
    package as a tuple. This is used during the bootstrap check to see if the
    version of the dependency has changed since the bootstrapped package was
    created.
    """
    return __version_tuple


### ---------------------------------------------------------------------------