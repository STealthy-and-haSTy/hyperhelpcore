import sublime

import os

from .bootstrapper import log, bootstrap_pkg, bootloader, BootstrapThread


### ---------------------------------------------------------------------------


def _should_bootstrap(settings):
    """
    Check to see if the bootstrap package needs to be created/updated or not.
    This checks both for the existence of the package as well as for when the
    bootstrapped version is different from ours.
    """
    # For debugging/testing/troubleshooting purposes, this allows you to set a
    # setting that forces the bootstrap to occur, even if it doesn't need to be
    # done.
    if settings.get("hyperhelp.force_bootstrap", False):
        log("hyperhelp bootstrap forced; skipping check")
        return True

    try:
        from importlib import __import__ as do_import
        from hyperhelpcore import __version__ as mp_sys_version

        mod = do_import("{pkg}.{file}".format(
                        pkg=bootstrap_pkg, file=bootloader),
                        fromlist=("__version__"))
        bootstrapped_version = mod.__dict__["__version__"]

        if bootstrapped_version == mp_sys_version:
            msg = "hyperhelpcore system package {pkg_name} is up to date (v{sys})"
        else:
            msg = "upgrading hyperhelpcore system package {pkg_name} from v{boot} to v{sys}"

        log(msg, sys=mp_sys_version, boot=bootstrapped_version, pkg_name=bootstrap_pkg)
        return not bootstrapped_version == mp_sys_version

    except:
        log("hyperhelpcore system package is missing ({pkg_name}); bootstrapping",
            pkg_name=bootstrap_pkg)

    return True


def initialize():
    """
    Ensures that the resource package that provides the syntax and other
    Sublime resources exists and is up to date; does nothing if this has
    already been called once.

    This *must* be invoked by all packages that are using hyperhelp actively
    and *must* be invoked after plugin_loaded() has been called, as it requires
    the Sublime API to be available.
    """
    if hasattr(initialize, "complete"):
        return

    initialize.complete = True

    settings = sublime.load_settings("Preferences.sublime-settings")
    ignored_packages = settings.get("ignored_packages", [])

    # Checks to see if the bootstrapped package is in the list of ignored
    # packages and complains if it is unless the user has also purposefully set
    # a setting telling us not to.
    #
    # This makes disabling the package a two step operation to stop potential
    # confusion on the behalf of the user, since they technically did not
    # install the bootstrapped package directly and might not know what it's
    # for.
    if bootstrap_pkg in ignored_packages:
        if settings.get("hyperhelp.ignore_disabled", False):
            return log("{pkg_name} package ignored; hyperhelp disabled",
                        pkg_name=bootstrap_pkg)

        return log(
            """
            The {pkg_name} package is currently disabled.

            Please remove this package from the
            `ignored_packages` setting and restart Sublime.

            If your intention was to disable {pkg_name},
            set the value of the 'hyperhelp.ignore_disabled'
            setting to True in your Preferences.sublime-settings
            file to remove this warning message at startup.
            """, pkg_name=bootstrap_pkg, error=True)

    # If the boostrapped package is overridden, the user will block themselves
    # from getting updates when the dependency updates. So check if that is the
    # case and generate an error and refuse to proceed.
    #
    # An undocumented setting exists to turn this from an error to just a log
    # warning instead, in which case we proceed.
    pkg_folder = os.path.join(sublime.packages_path(), bootstrap_pkg)
    if os.path.lexists(pkg_folder):
        if settings.get("hyperhelp.allow_unpacked", False) == False:
            return log(
                """
                The {pkg_name} package is unpacked.

                This package should not be overridden as it
                blocks updates and causes problems with
                bootstrapping.

                Please remove the {pkg_name} folder from
                the Packages folder and restart sublime.
                """, pkg_name=bootstrap_pkg, error=True)

        log("hyperhelpcore system package {pkg_name} is unpacked; issues may arise",
            pkg_name=bootstrap_pkg)

    if _should_bootstrap(settings):
        BootstrapThread().start()


### ---------------------------------------------------------------------------