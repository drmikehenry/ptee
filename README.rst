*******************************************************************************
"Progress Tee" - an enhanced "tee" program with in-place overwriting of status.
*******************************************************************************

Introduction
============

``ptee`` (for "Progress Tee") is a console utility that builds upon the basic
functionality provided by the standard Unix ``tee`` command.  It accepts lines
of text from a running command (such as an invocation of ``make``) and displays
them to the console such that consecutive less-important lines are overwritten
in-place, providing feedback regarding the progress of the overall operation
without allowing the more-important lines (such as compiler warnings and errors)
to scroll away and be overlooked.  In addition, as with standard ``tee``, a copy
of the text from stdin may optionally be written verbatim to one or more output
files.

These less-important lines are called "context" lines, as they provide context
leading up to the important lines; the more-important lines are called "regular"
lines.  Each new context overwrites previous context lines in-place on the
console, forming a "status" line that stays put without scrolling.  When a
regular line appears, the text composing the status line is kept (i.e., scrolled
up) to provide context for the regular text.

For example, suppose an invocation of ``make`` generates the following output::

  $ make
  gcc -c -Wall -W -o file1.o file1.c
  gcc -c -Wall -W -o file2.o file2.c
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]
  gcc -c -Wall -W -o file3.o file3.c
  gcc -c -Wall -W -o file4.o file4.c
  gcc -c -Wall -W -o file5.o file5.c
  gcc -o app file1.o file2.o file3.o file4.o file5.o

The compiler invocation lines (``gcc -c ...``) become uninteresting as soon as
the next line shows up, unless there are warnings or errors associated with that
invocation.  With ``ptee``, you can supply a regular expression to match these
"context" lines to allow them to overwrite each other on the console.  Lines not
matching the regular expression will be displayed on a line of their own (along
with the previous context line, if any).  In the above example, the output would
ultimately look like this::

  $ make 2>&1 | ptee --regex '^gcc'
  gcc -c -Wall -W -o file2.o file2.c
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]

The ``2>&1`` in the above invocation redirects stderr to the same location as
stdout, so that both stdout and stderr are piped into ``ptee``.  This is needed
because gcc's diagnostic messages go to stderr by default.

During the run of ``make``, each line of status will be written on top of the
previous line of status, providing continuous feedback while keeping the
interesting lines from scrolling too far off the screen.

Context Levels
==============

Context lines may have an associated level, indicating their position in a
hierarchy.  Levels are integers, starting at zero.  When a context line of
level N is detected, the status line will be built of the most recent lines of
context from levels zero through N, concatenated into a single status line.
This can be useful for retaining bigger-picture context information while
more detailed context information is coming in.

For example, consider a build system invoked with a script named ``buildall``,
which generates the following output::

  $ ./buildall
  x86:
  Building component1:
  [compile] file1.o
  [compile] file2.o
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]
  [link] component1
  Building component2:
  [compile] file3.o
  [link] component2
  x86_64:
  Building component3:
  [compile] file4.o
  [link] component3

In this build output, some components are being built, first for the x86
platform, then for the x86_64 platform.  This output has three levels of
context hierarchy:

- Level 0: the platform (``x86:`` or ``x86_64``);
- Level 1: the component (e.g., ``Building component1``);
- Level 2: the build step (e.g., ``[compile] source1``, ``[link] component3``).

Consider the following shell script to invoke ``buildall``::

  #!/bin/sh

  ./buildall 2>&1 | ptee build.out \
      --level-regex 0 '^(x86|x86_64):' \
      --level-regex 1 '^Building ' \
      --level-regex 2 '^\[.*\]'

The filename ``build.out`` is passed to ``ptee`` such that a verbatim copy of
the build output will be recorded in the file ``build.out`` for possible future
analysis.  When running ``./ba``, the uninteresting context lines are stripped
away, leaving only the regular lines (the warning message, in this case) and the
context lines at each level leading up to each regular line::

  $ ./ba
  x86:
  Building component1:
  [compile] file2.c
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]

More text actually goes to the console for status and feedback, but it is
overwritten by writing a carriage return (``\r``) instead of a newline (``\n``).
Below is the actual output, post-processed to show the carriage returns and the
subsequent overwriting taking place::

  x86:\r
  x86:  Building component1:\r
  x86:  Building component1:  [compile] file1.o\r
  x86:  Building component1:  [compile] file2.o\r
                                               \r
  x86:
  Building component1:
  [compile] file2.o
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]
  x86:  Building component1:  [link] component1\r
  x86:  Building component2:                   \r
  x86:  Building component2:  [compile] file3.o\r
  x86:  Building component2:  [link] component2\r
  x86_64:                                      \r
  x86_64:  Building component3:\r
  x86_64:  Building component3:  [compile] file4.o\r
  x86_64:  Building component3:  [link] component3\r

Notice that the status line that appears briefly during compilation of file1.c
contains all three levels of context line, and that the first two levels of
context are the same when subsequently compiling file2.c, so that
bigger-picture context persists longer in the status line::

  x86:  Building component1:  [compile] file1.o\r
  x86:  Building component1:  [compile] file2.o\r

Heading lines
=============

In addition to context lines, ``ptee`` supports the notion of "heading" line.
These lines do not contribute to the status line; instead, they are printed
as-is on the console.  Unlike regular lines, however, no context lines are
printed before a heading line.  This can be useful for long lines that would be
awkward if prepended to the status line.  Consider a second example with the
following modified output::

  $ ./buildall2
  ------------------------------ x86 ------------------------------
  Building component1:
  [compile] file1.o
  [compile] file2.o
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]
  [link] component1
  Building component2:
  [compile] file3.o
  [link] component2
  ------------------------------ x86_64 ---------------------------
  Building component3:
  [compile] file4.o
  [link] component3

The banner lines starting with ``------`` are too long to conveniently prepend
to the status line.  Instead, the ``ba2`` script treats them as headings::

  #!/bin/sh

  ./buildall2 2>&1 | ptee build.out \
    --heading-regex '^-----' \
    --level-regex 1 '^Building ' \
    --level-regex 2 '^\[.*\]'

Leading to this output::

  $ ./ba2
  ------------------------------ x86 ------------------------------
  Building component1:
  [compile] file2.o
  file2.c:1:12: warning: ‘x’ defined but not used [-Wunused-variable]
  ------------------------------ x86_64 ---------------------------

Skipping lines
==============

Sometimes input contains lines that should be skipped entirely, rather than
being treated as status lines.  An example might include spurious compiler
warnings that can't easily be suppressed.  The switch
``--skip-regex COUNT SKIP_REGEX`` provides a way to skip one or more lines that
match a given pattern.  For example, given the following input::

  [compile] file1.o
  system-header.h:999:18: warning: this is a spurious message
  in argument 2 of function `badly_written(x, y)`
  --------------------------------------------^
  [compile] file2.o

To skip the three lines of spurious warning, use this invocation::

  ptee --skip-regex 3 system-header.h:999:18:

This effectively transforms the input to::

  [compile] file1.o
  [compile] file2.o

Stripping overwritten lines
===========================

When writing to the console, status lines are continuously written and
overwritten to provide feedback on overall progress.  When the operation
completes, only the important lines of text remain.  But if this console output
were redirected to a file or piped into another program, the illusion of the
status lines being overwritten would fall apart, because all of the status lines
would be still be present in the output.  Therefore, when not writing to the
console, ``ptee`` strips out any status lines that would be overwritten.  This
default behavior can be overridden via the ``--strip`` option (to force the
status to be removed even when writing to a console) and the ``--no-strip``
option (to retain the status lines even when not writing to a console).  As an
example, the post-processed output shown above was generated something like
this::

  ./buildall 2>&1 | ptee [switches] --no-strip | perl -0777 -pe 's/\r/\\r\n/g'

Partial lines
=============

In general, ptee processes whole lines of text.  But sometimes the input stream
may pause after a partial line, such as when a program displays a prompt to the
user and pauses for a response.  To allow the user to see such partial lines,
ptee by default will wait an amount of time controlled by the
--partial-line-timeout switch; if the input stream stalls for longer than this
amount of time, the partial input will be displayed without further processing,
and all future input up to the next newline will be immediately displayed.
Setting the timeout value to zero disables the timeout feature.

Text encoding option
====================

By default, text is assumed to be in UTF-8 format on stdin and stdout.  This
may be overridden using the ``--encoding`` option, e.g., for a hypothetical
program that generates latin1 text::

  generate-latin1-text | ptee --encoding latin1 --regex '<regular expression>'

See ``ptee --help`` for more information.
