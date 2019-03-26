import sublime
import sublime_plugin

import textwrap

from hyperhelpcore.bootstrapper import log, BootstrapThread



###----------------------------------------------------------------------------


def _wrap(msg, *args, **kwargs):
    return textwrap.dedent(msg.format(*args, **kwargs)).strip()


def _is_developer_mode():
    s = sublime.load_settings("HyperHelp.sublime-settings")
    return s.get("developer_mode", False)


###----------------------------------------------------------------------------


class HyperhelpDeveloperForceBootstrapCommand(sublime_plugin.ApplicationCommand):
    """
    Verify with the user and then, if confirmed, force hyperhelpcore to run an
    immediate bootstrap sequence to re-bootstrap the package.

    This is a developer only command; if you're not actively developing the
    package, you shouldn't be invoking this command without being directed to
    do so by the developer or other person in the know.
    """
    def run(self):
        if sublime.yes_no_cancel_dialog(_wrap(
            """
            Force a HyperHelp bootstrap?

            This will execute a bootstrap and replace the existing
            HyperHelp system package (if any) with a newly generated
            one.
            """)) == sublime.DIALOG_YES:
            log("Developer: Forcing a bootstrap")
            BootstrapThread().start()

    def is_enabled(self):
        return _is_developer_mode()


###----------------------------------------------------------------------------
