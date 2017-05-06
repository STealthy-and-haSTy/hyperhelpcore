import sublime
import sublime_plugin

from .output_view import find_view, output_to_view


###----------------------------------------------------------------------------


def _help_focus(view, pos):
    pos = sublime.Region(pos.end(), pos.begin())

    view.show_at_center(pos)
    view.sel().clear()
    view.sel().add(pos)

    # Hack to make the view update properly.
    view.run_command("move", {"by": "characters", "forward": False})


###----------------------------------------------------------------------------


class HelpCommand(sublime_plugin.ApplicationCommand):
    def __init__(self):
        self._prefix = "Packages/%s/doc" % __name__.split(".")[0]
        self._loaded = False
        self._toc = dict()

    def _load_toc(self):
        if not self._loaded:
            self._loaded = True

            toc_file = "%s/index.json" % self._prefix

            try:
                json = sublime.load_resource(toc_file)
                self._toc = sublime.decode_value(json)

            except:
                print("Error loading help contents '%s'" % toc_file)

    def _load_help(self, help_file):
        if help_file is not None:
            filename = "%s/%s" % (self._prefix, help_file)
            try:
                return sublime.load_resource(filename)

            except:
                print("Unable to load help file %s" % filename)

        return None

    def _show_help_file(self, help_file):
        window = sublime.active_window()
        view = find_view(window, "HyperHelp")

        if view is not None:
            window.focus_view(view)
            current_file = view.settings().get("_hh_file", None)

            if current_file == help_file:
                return view

        help_txt = self._load_help(help_file)
        if help_txt is None:
            return sublime.error_message("Unable to open help\n\n"
                                         "Error opening '%s'" % help_file)

        view = output_to_view(window,
                              "HyperHelp",
                              help_txt,
                              syntax="Packages/HyperHelp/Help.sublime-syntax")
        view.settings().set("_hh_file", help_file)
        return view

    def _get_topic_file(self, topic):
        self._load_toc()
        return self._toc.get(topic, None)

    def _display_topic(self, topic):
        help_file = self._get_topic_file(topic)
        if help_file is None:
            return sublime.error_message("Unknown help topic: '%s'" % topic)

        help_view = self._show_help_file(help_file)
        if help_view is not None:
            for pos in help_view.find_by_selector('meta.link-target'):
                target = help_view.substr(pos)
                if target == topic:
                    return _help_focus(help_view, pos)

        return sublime.error_message("Unable to find topic '%s' in '%s'" % (topic, help_file))

    def _show_toc(self):
        self._load_toc()
        options = sorted([key for key in self._toc])

        def pick(index):
            if index >= 0:
                self._display_topic(options[index])

        sublime.active_window().show_quick_panel(options, pick)

    def _get_view_topic(self):
        view = sublime.active_window().active_view()
        point = view.sel()[0].begin()

        if view.match_selector(point, "text.help meta.link"):
            return view.substr(view.extract_scope(point))

        return None

    def run(self, toc=False, topic=None):
        if topic is None and not toc:
            topic = self._get_view_topic()

        if topic is None or toc:
            return self._show_toc()

        self._display_topic(topic)


###----------------------------------------------------------------------------


class HelpNavLinkCommand(sublime_plugin.WindowCommand):
    def run(self, prev=False):
        view = self.window.active_view()
        point = view.sel()[0].begin()

        targets = view.find_by_selector("meta.link")
        fallback = targets[-1] if prev else targets[0]

        def pick(pos):
            other = pos.begin()
            return (point < other) if not prev else (point > other)

        for pos in reversed(targets) if prev else targets:
            if pick(pos):
                return _help_focus(view, pos)

        _help_focus(view, fallback)


###----------------------------------------------------------------------------
