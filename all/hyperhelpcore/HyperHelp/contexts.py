import sublime
import sublime_plugin

from hyperhelpcore.common import log
from hyperhelpcore.common import current_help_package, current_help_file
from hyperhelpcore.view import find_help_view


###----------------------------------------------------------------------------


class HyperhelpContextListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        """
        Provide custom key binding contexts for binding keys in hyperhelp
        views.
        """
        if key == "hyperhelp.is_help_view":
            help_view = find_help_view(view.window())
            lhs = help_view is not None and help_view.id() == view.id()
            rhs = bool(operand)

        elif key == "hyperhelp.is_help_source":
            lhs = (view.match_selector(0, "text.hyperhelp.help") and
                   view.is_read_only() == False)
            rhs = bool(operand)

        elif key == "hyperhelp.is_help":
            lhs = view.match_selector(0, "text.hyperhelp.help")
            rhs = bool(operand)

        elif key == "hyperhelp.is_help_index":
            lhs = view.match_selector(0, "text.hyperhelp.index")
            rhs = bool(operand)

        elif key == "hyperhelp.is_help_visible":
            lhs = find_help_view(view.window()) is not None
            rhs = bool(operand)

        elif key == "hyperhelp.is_help_package":
            lhs = current_help_package(window=view.window())
            rhs = str(operand)

        elif key == "hyperhelp.is_help_file":
            lhs = current_help_file(window=view.window())
            rhs = str(operand)

        # This one is the legacy; remove this once the others are fully
        # tested.
        elif key == "hyperhelp.is_authoring":
            lhs = view.is_read_only() == False
            rhs = bool(operand)
        else:
            return None

        if operator == sublime.OP_EQUAL:
            return lhs == rhs
        elif operator == sublime.OP_NOT_EQUAL:
            return lhs != rhs

        return None


###----------------------------------------------------------------------------
