*********************************************************************************
"Progress Tee" - an enhanced "tee" program with in-place overwriting of "status".
*********************************************************************************

Introduction
============

``ptee`` (for "Progress Tee") is a console utility that builds upon the basic
functionality provided by the standard Unix ``tee`` command.  It accepts lines
of text from a running command (such as an invocation of ``make``) and displays
them to the terminal such that important lines of text (such as compiler errors)
are kept while lines of "status" information are overwritten in-place on one
line.

For example, suppose an invocation of ``make`` generates the following output::

  $ make
  gcc -c -Wall -W -o file1.o file1.c
  gcc -c -Wall -W -o file2.o file2.c
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]
  gcc -c -Wall -W -o file3.o file3.c
  gcc -c -Wall -W -o file4.o file4.c
  gcc -c -Wall -W -o file5.o file5.c

The compiler invocation lines (``gcc -c ...``) become uninteresting as soon as
the next line shows up, unless there are warnings or errors associated with that
invocation.  With ``ptee``, you can supply a regular expression to match these
types of "status" lines to allow them to overwrite each other on the terminal.
Lines not matching the regular expression will be displayed on a line of their
own (along with any previous line of status for context).  In the above example,
the output would ultimately look like this::

  $ make | ptee --regex gcc
  gcc -c -Wall -W -o file2.o file2.c
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]

During the run of ``make``, each line of status will be written on top of the
previous line of status, providing continuous feedback while keeping the
interesting lines from scrolling too far off the screen.

See ``ptee --help`` for more information.
