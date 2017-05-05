import sublime
import sublime_plugin

from .output_view import find_view, output_to_view


###----------------------------------------------------------------------------


def _help_focus(view, pos):
    pos = sublime.Region(pos.end(), pos.begin())

    view.show_at_center(pos)
    view.sel().clear()
    view.sel().add(pos)


###----------------------------------------------------------------------------


class HelpCommand(sublime_plugin.ApplicationCommand):
    def __init__(self):
        self._package = __name__.split(".")[0]
        self._prefix = "Packages/%s/doc/" % self._package

        self._files = dict()
        self._loaded = False

    def _load_files(self):
        if self._loaded:
            return

        self._loaded = True

        files = sublime.find_resources("*.txt")
        for name in filter(lambda name: name.startswith(self._prefix), files):
            root = name[len(self._prefix):]
            self._files[root] = name

    def _get_help_content(self, root_name):
        filename = self._files.get(root_name, None)
        if filename is not None:
            try:
                return sublime.load_resource(filename)
            except:
                pass
        return None

    def run(self, help_file="index.txt", topic=None):
        self._load_files()
        window = sublime.active_window()

        view = find_view(window, "HyperHelp")
        if view is not None:
            window.focus_view(view)

            current_file = view.settings().get("_hh_file", None)
            if current_file == help_file:
                if topic is not None:
                    view.run_command("help_follow_link", {"topic": topic})

                return

        help_txt = self._get_help_content(help_file)
        if help_txt is None:
            return sublime.error_message("Unable to open help\n\n"
                                         "Error opening '%s'" % help_file)

        view = output_to_view(window,
                              "HyperHelp",
                              help_txt,
                              syntax="Packages/HyperHelp/Help.sublime-syntax")
        view.settings().set("_hh_file", help_file)

        if topic is None:
            _help_focus(view, sublime.Region(0))
        else:
            view.run_command("help_follow_link", {"topic": topic})


###----------------------------------------------------------------------------


class HelpFollowLinkCommand(sublime_plugin.TextCommand):
    def run(self, edit, topic=None):
        if topic is None:
            point = self.view.sel()[0].begin()
            topic = self.view.substr(self.view.extract_scope(point))

        for pos in self.view.find_by_selector('meta.link-target'):
            target = self.view.substr(pos)
            if target == topic:
                return _help_focus(self.view, pos)

        sublime.run_command("help", {"help_file": topic})


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
