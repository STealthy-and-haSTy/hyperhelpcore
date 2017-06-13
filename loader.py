import imp
import sys


###----------------------------------------------------------------------------

# DEV ONLY
#
# This should not be here at release time; it's not needed since the package
# doesn't need to reload
def reload(modules=[""]):
    prefix = "hyperhelp.all."

    for module in modules:
        module = (prefix + module).rstrip(".")
        if module in sys.modules:
            imp.reload(sys.modules[module])


###----------------------------------------------------------------------------


reload()
from hyperhelp.all import HelpCommand, HelpNavLinkCommand, HelpListener


###----------------------------------------------------------------------------
