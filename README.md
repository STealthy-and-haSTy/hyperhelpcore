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
change without notice.

-------------------------------------------------------------------------------

<!--

## Installation ##

As a dependency, this package is not meant to be user installable. Instead,
your package should indicate that it needs `hyperhelp` as a dependency and
Package Control will install or update it as it installs packages that depend
on it.

See the [Package Control DependencyDocumenation](https://packagecontrol.io/docs/dependencies)
for more information on how to add a dependency for your package in order to use
`hyperhelp`.


### Manual Installation ###

Since `hyperhelp` is still under active development and has not had an official
release yet, the only way to make use of it currently is to manually install
it. You may also need to follow these steps if you are manually installing a
package that requires `hyperhelp`.


#### Package Control is not installed ####

If PackageControl is not installed, you can install the `hyperhelp` dependency
package manually using the following steps:

  1. Ensure that Sublime Text is not currently running
  2. Clone this repository directly into your `Packages` folder
  3. Rename `hyperhelp/loader.code` to `hyperhelp/loader.py`
  4. Start Sublime Text
  5. Verify the installation by selecting `HyperHelp: Help on Help` from the
     command palette, which should open help on `hyperhelp` itself.

#### Package Control is installed ####

If you are using Package Control, you can follow this series of steps to
manually install `hyperhelp` as a dependency.

To manually install, you can follow these steps.

  1. Ensure that Sublime Text is not currently running
  2. Clone this repository directly into your `Packages` folder
  3. Start Sublime Text, and then from the command palette select the command
     `Packge Control: Install Local Dependency` and select `hyperhelp` from the
     list of dependencies
  4. Start Sublime Text
  5. Verify the installation by selecting `HyperHelp: Help on Help` from the
     command palette, which should open help on `hyperhelp` itself.

Some version of Package Control have a bug which blocks the installation of a
local dependency when it uses custom loader code. If this is the case, in step
5 above you will be unable to find the appropriate command.

If this is the case, you need to complete the installation manually using the
following steps.

  1. Ensure that Sublime Text is not currently running
  2. Copy the file `Packages/hyperhelp/loader.code` to the file
     `Installed Packages/01-hyperhelp.py`
  3. Move the file `01-hyperhelp.py` into the file `0_package_control_loader.sublime-package`,
     which is actually a `zip` file (See below).
  4. Restart Sublime Text and use step 5 above to verify that the installation
     was successful.

The file `0_package_control_loader.sublime-package` in the `Installed Packages`
folder is a zip file with a different extension. For MacOS and Linux, you can
use the following command from within the `Installed Packages` folder to add
the hyperhelp loader to the package and remove it from the current directory
all in one step:

    zip -m 0_package_control_loader.sublime-package 01-hyperhelp.py

On Windows you can do this by temporarily renaming the `sublime-package` file
to have a `zip` extension instead, then double click it to open it as a
compressed folder and move the file inside. Be sure to rename the file back to
a `sublime-package` extension when you're done, then verify the success of the
install with step 5 above.


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

-->

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
