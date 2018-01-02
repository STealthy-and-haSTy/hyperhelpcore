import sublime
import sublime_plugin

from .core import help_index_list, lookup_help_topic


###----------------------------------------------------------------------------


_help_popup = """
<body id="hyperhelp-link-caption">
    <style>
        body {
            font-family: system;
            margin: 0.5rem 1rem;
        }
        h1 {
            font-size: 1.1rem;
            font-weight: bold;
            margin: 0 0 1rem 0;
            border-bottom: 2px solid var(--foreground);
        }
        p {
            font-size: 1.05rem;
            margin: 0;
        }
        .indent {
            margin-left: 1.5rem;
        }
     </style>
     %s
</body>
"""

_topic_body = """
<h1>%s</h1>
<p>%s</p>
<p class="indent">%s</p>
"""

_missing_body = """
<h1>Missing Topic</h1>
<p>Topic not in help index:</p>
<p class="indent">%s</p>
"""


###----------------------------------------------------------------------------


class HyperhelpEventListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        """
        Provide custom key binding contexts for binding keys in hyperhelp
        views.
        """
        if key == "hyperhelp.is_authoring":
            lhs = view.is_read_only() == False
            rhs = bool(operand)
        else:
            return None

        if operator == sublime.OP_EQUAL:
            return lhs == rhs
        elif operator == sublime.OP_NOT_EQUAL:
            return lhs != rhs

        return None

    def on_text_command(self, view, command, args):
        """
        Listen for the drag_select command with arguments that tell us that the
        user double clicked, see if they're double clicking on a link so we
        know if we should try to follow it or not.
        """
        if (view.is_read_only() and command == "drag_select" and
                args.get("by", None) == "words"):
            event = args["event"]
            point = view.window_to_text((event["x"], event["y"]))

            if view.match_selector(point, "text.hyperhelp meta.link"):
                view.window().run_command("hyperhelp_navigate",
                                         {"nav": "follow_link"})
                return ("noop")

        return None

    def on_hover(self, view, point, hover_zone):
        """
        If the mouse hovers over a link in a help view, show a popup that
        says where the link goes.
        """
        if hover_zone != sublime.HOVER_TEXT:
            return

        pkg = view.settings().get("_hh_pkg", None)
        if pkg is None or not view.score_selector(point, "meta.link"):
            return

        pkg_info = help_index_list().get(pkg, None)
        if pkg_info is None:
            return

        topic = view.substr(view.extract_scope(point))
        topic_data = lookup_help_topic(pkg_info, topic)
        if topic_data is None:
            popup = _missing_body % topic
        else:
            caption = topic_data["caption"]
            file = topic_data["file"]

            if file in pkg_info.urls:
                link_type = "Opens URL: "
            elif file in pkg_info.package_files:
                link_type = "Opens File: "
            else:
                link_type = "Links To: "
                current_file = view.settings().get("_hh_file", None)
                if file == current_file:
                    file = "this file"

            popup = _topic_body % (caption, link_type, file)

        view.show_popup(
            _help_popup % popup,
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
            location=point,
            max_width=1024)


###----------------------------------------------------------------------------
