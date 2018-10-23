import sublime
import sublime_plugin

from .core import help_index_list, lookup_help_topic
from .view import find_help_view
from .help import _get_link_topic


###----------------------------------------------------------------------------


_help_popup = """
<body id="hyperhelp-link-caption">
    <style>
        body {{
            font-family: system;
            margin: 0.5rem 1rem;
        }}
        h1 {{
            font-size: 1.2rem;
            font-weight: bold;
            margin: 0 0 1rem 0;
            border-bottom: 2px solid var(--foreground);
        }}
        p {{
            font-size: 1.05rem;
            margin: 0;
        }}
        .body {{
            margin-bottom: 1rem;
        }}
        .details {{
            margin-left: 1.5rem;
            font-family: monospace;
        }}
     </style>
     {body}
</body>
"""

_missing_pkg = """
<h1>Package not found</h1>
<p class="body">This link references a help package that is
   not currently installed.</p>
<p class="details">{pkg} / {topic}</p>
"""

_missing_topic = """
<h1>Topic not found</h1>
<p class="body">This link references a topic that does not appear
   in the help index.</p>
<p class="details">{pkg} / {topic}</p>
"""

_missing_file = """
<h1>Package File not found</h1>
<p class="body">This link opens a package file that does not
   currently exist.</p>
<p class="details">{file}</p>
"""


_topic_body = """
<h1>{title}</h1>
<p class="body">{link_type}</p>
<p class="details">{link}</p>
"""


###----------------------------------------------------------------------------


def plugin_loaded():
    for window in sublime.windows():
        view = find_help_view(window)
        if view:
            view.run_command("hyperhelp_internal_flag_links")


def _show_popup(view, point, popup):
    view.show_popup(
        _help_popup.format(body=popup),
        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
        location=point,
        max_width=1024)


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
        When the mouse hovers over a link in a help view, show a popup that
        tells you where the link goes or what file/URL it opens.
        """
        if hover_zone != sublime.HOVER_TEXT:
            return

        default_pkg = view.settings().get("_hh_pkg", None)
        if default_pkg is None or not view.score_selector(point, "meta.link"):
            return

        link_info = _get_link_topic(view, view.extract_scope(point))
        if link_info is None:
            return

        pkg = link_info.get("pkg", default_pkg)
        topic = link_info.get("topic")

        # Report if we don't know the package. In this case we may know what
        # the topic is but not what file it might appear in.
        pkg_info = help_index_list().get(pkg, None)
        if pkg_info is None:
            popup = _missing_pkg.format(pkg=pkg, topic=topic)
            return _show_popup(view, point, popup)

        # If there is no topic we can't really display anything useful. This is
        # an exceptional situation that is only possible if the help is broken.
        if topic is None:
            return

        # Look up the topic details. If we can't find it in the index, react
        # like a missing package since we can't know the file.
        topic_data = lookup_help_topic(pkg_info, topic)
        if topic_data is None:
            popup = _missing_topic.format(pkg=pkg, topic=topic)
            return _show_popup(view, point, popup)

        caption = topic_data.get("caption")
        file = topic_data.get("file")
        link = file

        # For links that open files, if that file does not exist as far as
        # Sublime is concerned, use a custom popup to let the user know. Such
        # a link will be highlighted as broken, so this explains why.
        if file in pkg_info.package_files and not sublime.find_resources(file):
            popup = _missing_file.format(file=file)
            return _show_popup(view, point, popup)

        if file in pkg_info.urls:
            link_type = "Opens URL: "
        elif file in pkg_info.package_files:
            link_type = "Opens File: "
        else:
            link_type = "Links To: "

            link = "" if default_pkg == pkg else pkg + " / "

            current_file = view.settings().get("_hh_file", None)
            if file != current_file:
                link = link + file + " / "

            link = link + topic

        popup = _topic_body.format(title=caption or topic,
                                   link_type=link_type,
                                   link=link)

        _show_popup(view, point, popup)


###----------------------------------------------------------------------------
