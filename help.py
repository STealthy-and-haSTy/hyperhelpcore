import sublime
import sublime_plugin

from .output_view import find_view, output_to_view


###----------------------------------------------------------------------------


def plugin_loaded():
    HelpIndex()


def plugin_unloaded():
    HelpIndex.unregister()


def _help_focus(view, pos):
    pos = sublime.Region(pos.end(), pos.begin())

    view.show_at_center(pos)
    view.sel().clear()
    view.sel().add(pos)


###----------------------------------------------------------------------------


class HelpIndex():
    """
    A singleton class that manages the help index for all help files.
    """
    instance = None

    def __init__(self):
        if HelpIndex.instance is not None:
            return

        HelpIndex.instance = self

        self._pkg_name = __name__.split(".")[0]
        self._pkg_prefix = "Packages/%s/doc/" % self._pkg_name

        self._files = dict()
        for name in self.__get_help_files():
            root = name[len(self._pkg_prefix):]
            self._files[root] = name


    def __get_help_files(self):
        return [f for f in sublime.find_resources("*.txt") if f.startswith(self._pkg_prefix)]

    @classmethod
    def unregister(cls):
        if HelpIndex.instance is not None:
            HelpIndex.instance = None

    @classmethod
    def has_help_file(cls, root_name):
        return root_name in cls.instance._files

    @classmethod
    def get_help_content(cls, root_name):
        filename = cls.instance._files.get(root_name, None)
        if filename is not None:
            try:
                return sublime.load_resource(filename)
            except:
                pass
        return None


###----------------------------------------------------------------------------


class HelpOpenCommand(sublime_plugin.WindowCommand):
    """
    Open the provided help file, optionally also focused on the topic provided.
    """
    def run(self, help_file="index.txt", topic=None):
        # Is there an existing help window?
        view = find_view(self.window, "HyperHelp")
        if view is not None:
            self.window.focus_view(view)

            # If it's already open, we're done, but if there is a topic passed
            # in, jump directly to it.
            current_file = view.settings().get("_hh_file", None)
            if current_file == help_file:
                if topic is not None:
                    view.run_command("help_follow_link", {"topic": topic})

                return

        # Help is not open, or it is but it's not the correct file. Proceed to
        # load the help file now.
        help_txt = HelpIndex.get_help_content(help_file)
        if help_txt is None:
            return sublime.error_message("Unable to open help\n\n"
                                         "Error opening '%s'" % help_file)

        # Send it out, possibly replacing the help content of an existing view.
        view = output_to_view(self.window,
                              "HyperHelp",
                              help_txt,
                              syntax="Packages/HyperHelp/Help.sublime-syntax")
        view.settings().set("_hh_file", help_file)

        # Set view location; either jump to the top of the file or navigate to
        # the topic now.
        if topic is None:
            _help_focus(view, sublime.Region(0))
        else:
            view.run_command("help_follow_link", {"topic": topic})


###----------------------------------------------------------------------------


class HelpFollowLinkCommand(sublime_plugin.TextCommand):
    def run(self, edit, topic=None):
        # Get topic to follow from the cursor location if not given
        if topic is None:
            point = self.view.sel()[0].begin()
            topic = self.view.substr(self.view.extract_scope(point))

        # Try to find it in the buffer.
        for pos in self.view.find_by_selector('meta.link-target'):
            target = self.view.substr(pos)
            if target == topic:
                return _help_focus(self.view, pos)

        # If we get here, see if the topic is a file and open it.
        if HelpIndex.has_help_file(topic):
            self.view.window().run_command("help_open", {"help_file": topic})
        else:
            sublime.status_message("No help file '%s' found" % topic)


###----------------------------------------------------------------------------


class HelpSelectLinkCommand(sublime_plugin.TextCommand):
    def run(self, edit, previous=False):
        point = self.view.sel()[0].begin()
        targets = self.view.find_by_selector("meta.link")
        fallback = targets[-1] if previous else targets[0]

        def pick(pos):
            other = pos.begin()
            return (point < other) if not previous else (point > other)

        for pos in reversed(targets) if previous else targets:
            if pick(pos):
                return _help_focus(self.view, pos)

        _help_focus(self.view, fallback)


###----------------------------------------------------------------------------
