
This plugin requires VSCode version 1.45, or later.

Installing as a Package
=======================

The extension bundle can be created using the npm package ``vsce``

.. code-block::

   $ cd extras/csl.vscode
   $ npx vsce package
   ...
   DONE  Packaged: .../extras/csl.vscode/csl-0.0.1.vsix (16 files, 35.82KB)
   $

At this point, goto the extension panel, View > Extensions on OSX,
click the ..., Install from VSIX, and then select the generated
csl-\*.vsix file.

Manually Installing
===================

To start using this extension with Visual Studio Code copy it into the
``<user home>/.vscode/extensions`` folder and restart Code. Specifically,
create a directory for this package, and move the following files
into this new extensions directory.

.. code-block::

   $ cd extras/csl.vscode
   $ mkdir ~/.vscode/extensions/cerebras.csl-0.0.1
   $ cp language-configuration.json ~/.vscode/extensions/cerebras.csl-0.0.1
   $ cp package.json ~/.vscode/extensions/cerebras.csl-0.0.1
   $ cp README.rst ~/.vscode/extensions/cerebras.csl-0.0.1
   $ mkdir ~/.vscode/extensions/cerebras.csl-0.0.1/syntaxes
   $ cp syntaxes/csl.tmLanguage.json \
       ~/.vscode/extensions/cerebras.csl-0.0.1/syntaxes
   $ mkdir ~/.vscode/extensions/cerebras.csl-0.0.1/images
   $ cp images/cerebras-icon.png ~/.vscode/extensions/cerebras.csl-0.0.1/images

Alternatively, if you are using the ``Remote - SSH`` extension to connect
to your development machine, a symbolic link is all you need:

.. code-block::

   $ cd ~/.vscode-server/extensions
   $ ln -s /path/to/cslang/extras/csl.vscode cerebras.csl-0.0.1
