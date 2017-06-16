HyperHelp
=========

HyperHelp is a dependency package for Sublime Text 3 that allows package
authors to provide context sensitive, hyperlinked help for their packages that
is displayable directly from within Sublime Text.

HyperHelp contains the core commands and integrations to allow for the display
and navigation of simple help documents so that all package authors need to do
is write the help itself.


-------------------------------------------------------------------------------

**NOTE:** This is very much still a work in progress and still being actively
developed and tweaked. At this point anything and everything is subject to
change without notice. Ironically, as a system purpose built to provide help,
during development what documentation there is may be potentially out of date
as things change.

-------------------------------------------------------------------------------


## Installation ##

Since the package is still in development, the only supported installation
method is a manual one.

To install, you can clone this repository directly into your `Packages` folder,
then from within Sublime choose `Package Control: Install Local Dependency`
from the command palette and select `hyperhelp` from the list.


-------------------------------------------------------------------------------


## Usage ##

Once installed, the following commands are added to the command palette to allow
you to interface with the help system.

Note that other commands may exist as well if a package author adds some help
commands of their own.


### `HyperHelp: Help on Help` ###

This opens the help system inside of a new view, showing you the index file of
the help for HyperHelp itself (currently a bit out of date).


### `HyperHelp: Table of Contents` ###

This command will only be visible in the command palette when help is open, and
displays a quick panel showing a hierarchical table of contents which is
specific to the help for the package that is currently open.

Selecting a topic from the list will either drill down into the contents or open
the selected help topic, depending on the item selected.


### `HyperHelp: List Available Help` ###

This command will display a quick panel that allows you to select a package
from the list of all packages currently installed which are providing help via
HyperHelp.

Selecting a package from the list will show you the table of contents for that
help package the same as the `HyperHelp: Table of Contents` command does,
allowing you to select a topic to display.


-------------------------------------------------------------------------------


## Navigating Help ##

While inside of a help view, the standard navigation for any file open in
Sublime is available to you to move around, copy data out, etc.

Text in vertical pipes is a `|Link|`, and double clicking on one or pressing
`Enter` while the cursor is inside of one will cause the help system to jump to
the target of the link.

Text in `*Asterisks*` and `'Single Quotes'` are "Link Targets", and specify a
location that a link somewhere else can jump to.

Pressing the `Tab` or `Shift+Tab` allows you to skip the caret to the next or
previous `|Link|` or `*Target*` in the document, allowing for easier
navigation.


-------------------------------------------------------------------------------


## License ##

Copyright 2017 Terence Martin

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
