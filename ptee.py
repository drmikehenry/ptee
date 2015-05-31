#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)

__version__ = '0.1.0'

description = """\
Enhanced "tee" function.
"""

epilog = """\
- Input is always written unmodified to specified OUTFILEs.
- Input (possibly modified) will be written to standard out.
- Lines are of three kinds:
  - HEADING lines matching the supplied HEADING_REGEX;
  - STATUS lines matching the supplied REGEX but not the HEADING_REGEX;
  - REGULAR lines not matching either regex.
- REGULAR and HEADING lines are never overwritten.
- STATUS lines may be overwritten by subsequent STATUS or HEADING lines.
- REGULAR lines do not overwrite STATUS lines (which are saved for context).
- When --strip is supplied, any overwritten lines are removed entirely; by
  default, --strip is active when stdout is not a TTY.
- Multiple --regex options will be joined with the logical "OR" operator, '|'
  (and similarly for --heading-regex options).
"""

import sys
import os
import io
import re
import logging
import argparse
from contextlib import closing


logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))


class Tee(object):
    def __init__(self):
        # Holds contents of most recent "status" line.
        self.last_status_line = ''
        self.ditto_files = []
        self._strip = False
        self._outfile = sys.stdout
        self._regex = ''
        self._heading_regex = ''

    @property
    def outfile(self):
        return self._outfile

    @outfile.setter
    def outfile(self, outfile):
        self._outfile = outfile

    @property
    def regex(self):
        return self._regex

    @regex.setter
    def regex(self, regex):
        self._regex = regex

    @property
    def heading_regex(self):
        return self._heading_regex

    @heading_regex.setter
    def heading_regex(self, heading_regex):
        self._heading_regex = heading_regex

    @property
    def strip(self):
        return self._strip

    @strip.setter
    def strip(self, strip):
        self._strip = strip

    def fwrite(self, f, s):
        """Flushed write to file."""

        f.write(s)
        f.flush()

    def write(self, s):
        self.fwrite(self.outfile, s)

    def write_status(self, status):
        status = status.rstrip()
        padded_status = status.ljust(len(self.last_status_line))
        if padded_status and not self.strip:
            self.write(padded_status + '\r')
        self.last_status_line = status

    def keep_status(self):
        if self.last_status_line:
            if self.strip:
                self.write(self.last_status_line + '\n')
            else:
                self.write('\n')
            self.last_status_line = ''

    def flush(self):
        self.write_status('')

    def put_line(self, line):
        for f in self.ditto_files:
            self.fwrite(f, line)
        if self.heading_regex and re.search(self.heading_regex, line):
            self.write_status(line)
            self.keep_status()
        elif self.regex and re.search(self.regex, line):
            self.write_status(line)
        else:
            self.keep_status()
            self.write(line)

    def add_ditto_file(self, ditto_file):
        self.ditto_files.append(ditto_file)

    def open_ditto_file(self, ditto_file, append=False):
        mode = 'a' if append else 'w'
        self.add_ditto_file(io.open(ditto_file, mode))

    def close_ditto_files(self):
        while self.ditto_files:
            self.ditto_files.pop().close()

    def close(self):
        self.flush()
        self.close_ditto_files()

    def drain(self, infile):
        while True:
            line = infile.readline()
            if line:
                self.put_line(line)
            else:
                break

# For make invocations.
MAKE_REGEX = (
    r'^\s+\[.+\]|'
    r'^\w*make\[\d+\]: (`|Entering |Leaving |Nothing )|'
    r'^\w*make -r |'
    r'^\w+ finished$|'
    r'^(\S*/)?\bgcc\s|'
    r'\.\.\. (ok|SKIPPED)$|'
    r'Running group|'
    r'Ending group|'
    r'All tests passed|'
    r'^\s+EndSuite:.*FAILED: 0, ERRORS: 0,|'
    r'^\s*Suite:'
)


def regex_to_str(regex):
    return "'" + regex + "'"


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
    parser.add_argument('-v',
                        '--verbose',
                        action='store_const',
                        dest='verbose',
                        const=logging.DEBUG,
                        help='verbose output for debugging')
    parser.add_argument('-q',
                        '--quiet',
                        action='store_const',
                        dest='verbose',
                        const=logging.WARNING,
                        help='suppress informational output')
    parser.add_argument('--regex',
                        action='append',
                        dest='regex_list',
                        default=[],
                        metavar='REGEX',
                        help='append a "status" regular expression (e.g., ' +
                        regex_to_str(r'^#.*') + ' for comment lines)')
    parser.add_argument('--heading-regex',
                        action='append',
                        dest='heading_regex_list',
                        default=[],
                        metavar='HEADING_REGEX',
                        help='append a "heading" regular expression (e.g., ' +
                        regex_to_str(r'^:: ') + ' for heading lines)')
    parser.add_argument('--make',
                        action='append_const',
                        dest='regex_list',
                        const=MAKE_REGEX,
                        help='short for --regex ' + regex_to_str(MAKE_REGEX) +
                        '; useful for the output of a `make` invocation')
    parser.add_argument('--strip',
                        action='store_true',
                        dest='strip',
                        default=None,
                        help="""strip out informational output that does not
                        immediately precede non-informational output, rather
                        than display and overwrite it in place; defaults to
                        --no-strip when stdout is a TTY and --strip otherwise.
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
    if args.verbose is None:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(args.verbose)
    tee = Tee()
    tee.regex = '|'.join(args.regex_list)
    tee.heading_regex = '|'.join(args.heading_regex_list)
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
