import sublime

from hyperhelpcore.bootstrapper import display_topic
from hyperhelpcore.common import hh_setting


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


def plugin_loaded():
    """
    On plugin load, see if we should display an initial help topic or not.
    This relies on a window setting that the bootstrapper applies to whatever
    the current window is, and will display an appropriate topic based on what
    the bootstrap did.
    """
    topic = None
    for window in sublime.windows():
        settings = window.settings()
        if settings.has("hyperhelp.initial_topic"):
            topic = topic or settings.get("hyperhelp.initial_topic")
            settings.erase("hyperhelp.initial_topic")

    if topic is not None and hh_setting("show_changelog"):
        package, topic = topic.split(":")
        display_topic(package, topic)


### ---------------------------------------------------------------------------