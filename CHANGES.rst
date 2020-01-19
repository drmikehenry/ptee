*******
History
*******

Version 0.4.0
=============

- Remove Python 2 support.

- Use new Python tooling: pip-tools, black, mypy, tox, pytest-style tests

Version 0.3.2
=============

- Change default --partial-line-timeout to 2.0.

Version 0.3.1
=============

- Allow partial lines to be processed promptly.

  --partial-line-timeout controls the amount of time to wait for the rest of a
  line to arrive; if the line times out, its parts will be processed
  immediately, and they will not be subject to comparison with any regular
  expressions.  This helps with things like password prompts in the input
  stream.


- Add ``--skip-regex COUNT REGEX`` feature for skipping lines entirely.

  If a line matches REGEX, COUNT lines will be skipped entirely.  This is
  useful for removing spurious lines of input before additional
  processing.

- Setup for Travis CI and py.test.
