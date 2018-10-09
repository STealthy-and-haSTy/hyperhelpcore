import sublime


_get_window = lambda wnd: wnd if wnd is not None else sublime.active_window()


###----------------------------------------------------------------------------


def find_help_view(window=None):
    """
    Search for and return the help view in the provided window. Defaults to
    searching the current window if none is provided.
    """
    window = window if window is not None else sublime.active_window()
    for view in window.views():
        if view.name().startswith("HyperHelp"):
            s = view.settings()
            if s.has("_hh_pkg") and s.has("_hh_file"):
                return view


def new_help_view(syntax=None, window=None):
    """
    Create and return a new help view in the provided window. Defaults to the
    current window if none is specified.
    """
    hView = _get_window(window).new_file()
    hView.set_scratch(True)
    hView.set_name("HyperHelp")

    if syntax is not None:
        hView.assign_syntax(syntax)

    return hView


def update_help_view(help_content, help_pkg, help_file,
                     syntax=None, window=None):
    """
    Find or create the help view in the provided window and set it's contents
    to the help string provided. The help view will have it's internal state
    set up to track the given help package and file.
    """
    window = _get_window(window)
    help_view = find_help_view(window)

    if help_view is None:
        help_view = new_help_view(syntax, window)
    else:
        help_view.set_read_only(False)
        help_view.run_command("select_all")
        help_view.run_command("left_delete")

        if window.active_view() != help_view:
            window.focus_view(help_view)

    help_view.settings().set("_hh_pkg", help_pkg)
    help_view.settings().set("_hh_file", help_file)

    help_view.run_command("append", {"characters": help_content})
    help_view.set_read_only(True)

    return help_view


###----------------------------------------------------------------------------
