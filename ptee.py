#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)

__version__ = '0.2.0'

description = """\
Enhanced "tee" function.
"""

epilog = """\
- Input is always written unmodified to specified OUTFILEs.
- Input (possibly modified) will be written to standard out.
- Lines are of three kinds (in priority order):
  - HEADING lines matching the supplied HEADING_REGEX;
  - CONTEXT lines matching the supplied REGEX at a given LEVEL;
  - REGULAR lines not matching any regex.
- REGULAR and HEADING lines are never overwritten.
- CONTEXT lines may be overwritten.
- When --strip is supplied, any overwritten lines are removed entirely; by
  default, --strip is active when stdout is not a TTY.
- Multiple regular expressions of the same type will be joined with the logical
  "OR" operator, '|'.
"""

import sys
import os
import io
import re
import argparse
from contextlib import closing


def fwrite(file, string):
    """Flushed write to file."""

    file.write(string)
    file.flush()


def regex_join(*regexes):
    """Join regular expressions with logical-OR operator '|'.

    Args:
        *regexes: regular expression strings to join.

    Return:
        Joined regular expression string.
    """
    regex = '|'.join([r for r in regexes if r])
    return regex


class Tee(object):
    def __init__(self):
        self._last_status = ''
        self._ditto_files = []
        self._strip = False
        self._outfile = sys.stdout
        self._regexes = []
        self._heading_regex = ''
        self._heading = ''
        self._context_lines = []
        self._display_level = 0

    @property
    def outfile(self):
        return self._outfile

    @outfile.setter
    def outfile(self, outfile):
        self._outfile = outfile

    @property
    def strip(self):
        return self._strip

    @strip.setter
    def strip(self, strip):
        self._strip = strip

    def append_level_regex(self, level, regex):
        while level >= len(self._regexes):
            self._regexes.append(r'')
        self._regexes[level] = regex_join(self._regexes[level], regex)

    def append_heading_regex(self, regex):
        self._heading_regex = regex_join(self._heading_regex, regex)

    def _write(self, string):
        fwrite(self.outfile, string)

    def write_status(self, status):
        if not self.strip:
            status = status.rstrip()

            # TODO Reduce status length based on TTY columns.
            padded_status = status.ljust(len(self._last_status))
            if padded_status:
                self._write(padded_status + '\r')
            self._last_status = status

    def erase_status(self):
        if self._last_status:
            self._write(' ' * len(self._last_status) + '\r')
            self._last_status = ''

    def write(self, line):
        self.erase_status()
        self._write(line)

    def clear_context(self):
        self._context_lines = []
        self._display_level = 0

    def set_context(self, level, context):
        if self._display_level > level:
            self._display_level = level
        del self._context_lines[level + 1:]
        while level >= len(self._context_lines):
            self._context_lines.append('')
        self._context_lines[level] = context
        lines = [s.rstrip() for s in self._context_lines]
        lines = [line for line in lines if line]
        self.write_status('  '.join(lines))

    def show_context(self):
        end_level = len(self._context_lines)
        for level in range(self._display_level, end_level):
            self.write(self._context_lines[level])
        self._display_level = end_level

    def put_line(self, line):
        for f in self._ditto_files:
            fwrite(f, line)
        if self._heading_regex and re.search(self._heading_regex, line):
            self.clear_context()
        for level, regex in enumerate(self._regexes):
            if regex and re.search(regex, line):
                self.set_context(level, line)
                break
        else:
            self.show_context()
            self.write(line)

    def add_ditto_file(self, ditto_file):
        self._ditto_files.append(ditto_file)

    def open_ditto_file(self, ditto_file, append=False):
        mode = 'a' if append else 'w'
        self.add_ditto_file(io.open(ditto_file, mode))

    def close_ditto_files(self):
        while self._ditto_files:
            self._ditto_files.pop().close()

    def close(self):
        self.erase_status()
        self.close_ditto_files()

    def drain(self, infile):
        while True:
            line = str(infile.readline())
            if line:
                self.put_line(line)
            else:
                break

DEFAULT_LEVEL = 2
"""Default LEVEL value for --regex switch."""


def inner_main():
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument('-a',
                        '--append',
                        action='store_true',
                        dest='append',
                        help='append to given files, do not overwrite')
    parser.add_argument('--regex',
                        action='append',
                        dest='regexes',
                        default=[],
                        metavar='REGEX',
                        help="""append "CONTEXT" regular expression for
                        the default LEVEL; equivalent to
                        ``--level-regex %s REGEX``""" % DEFAULT_LEVEL)
    parser.add_argument('--level-regex',
                        action='append',
                        dest='level_regexes',
                        nargs=2,
                        default=[],
                        metavar='LEVEL REGEX',
                        help="""append "CONTEXT" regular expression for given
                        LEVEL; zero is highest-order level""")
    parser.add_argument('--heading-regex',
                        action='append',
                        dest='heading_regexes',
                        default=[],
                        metavar='HEADING_REGEX',
                        help='append a "HEADING" regular expression')
    parser.add_argument('--strip',
                        action='store_true',
                        dest='strip',
                        default=None,
                        help="""remove any status that gets overwritten by
                        subsequent lines, rather than display and overwrite it
                        in-place; defaults to --no-strip when stdout is a TTY
                        and --strip otherwise
                        """)
    parser.add_argument('--no-strip',
                        action='store_false',
                        dest='strip',
                        help="""turn off --strip option""")
    parser.add_argument('files',
                        nargs='*',
                        metavar='OUTFILE',
                        help="""an unmodified copy of stdin is written to each
                        output file""")

    args = parser.parse_args()
    tee = Tee()
    for level, regex in args.level_regexes:
        try:
            level = int(level)
        except ValueError:
            parser.error('invalid LEVEL %s' % repr(level))
        tee.append_level_regex(int(level), regex)
    for regex in args.regexes:
        tee.append_level_regex(DEFAULT_LEVEL, regex)
    for regex in args.heading_regexes:
        tee.append_heading_regex(regex)
    if args.strip is None:
        tee.strip = not os.isatty(sys.stdout.fileno())
    else:
        tee.strip = args.strip
    with closing(tee):
        for name in args.files:
            tee.open_ditto_file(name, append=args.append)
        tee.drain(sys.stdin)


def main():
    try:
        inner_main()
    except KeyboardInterrupt:
        print('\nptee: keyboard interrupt', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
