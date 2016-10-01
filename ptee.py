#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)

import codecs
import sys
import os
import io
import re
import argparse
import queue
import threading

try:
    from blessed import Terminal
    _term = Terminal()
except ImportError:
    _term = None


__version__ = '0.3.2'

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
- ptee waits up to --partial-line-timeout seconds for a partial line to
  completely arrive; on timeout, the partial line will be processed immediately
  along with all future input up to the next newline.  Lines interrupted by a
  timeout are never compared to any REGEX (i.e., they are REGULAR lines).  Use
  a timeout value of 0 to disable the timeout feature.
"""


_term_width = 80
"""Width of terminal in columns."""


def get_terminal_width():
    return _term_width


def set_terminal_width(width):
    global _term_width
    _term_width = width


def track_terminal_width():
    if not _term:
        return
    set_terminal_width(_term.width)
    try:
        import signal
    except ImportError:
        return
    try:
        signum = signal.SIGWINCH
    except AttributeError:
        return

    def handler(sig, action):
        set_terminal_width(_term.width)

    signal.signal(signum, handler)
    signal.siginterrupt(signum, False)


def std_binfile(std_file):
    """Return binary-mode equivalent for std_file (stdin or stdout)."""
    # If .buffer exists, it will be the Python 3 underlying buffer object
    # which is in binary; if not, then it's Python 2 where stdin/stdout
    # are already in binary mode.
    return getattr(std_file, 'buffer', std_file)


def stdout_writer(encoding):
    return codecs.getwriter(encoding)(std_binfile(sys.stdout),
                                      errors='replace')


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


class Progress(object):
    def __init__(self):
        self._last_status = ''
        self._strip = False
        self._outfile = stdout_writer('utf-8')
        self._regexes = []
        self._heading_regex = ''
        self._count_skip_regexes = []
        self._heading = ''
        self._context_lines = []
        self._display_level = 0
        self._width = 0
        self._text_parts = []
        self._within_partial_line = False
        self._num_lines_to_skip = 0

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

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        self._width = width

    def append_level_regex(self, level, regex):
        while level >= len(self._regexes):
            self._regexes.append(r'')
        self._regexes[level] = regex_join(self._regexes[level], regex)

    def append_heading_regex(self, regex):
        self._heading_regex = regex_join(self._heading_regex, regex)

    def append_count_skip_regex(self, count, skip_regex):
        self._count_skip_regexes.append((count, skip_regex))

    def close(self):
        self.flush()
        self._erase_status()

    @property
    def have_unwritten_data(self):
        return len(self._text_parts) != 0

    def flush(self):
        self._write_text_parts(flush=True)

    def write(self, text):
        if text:
            self._text_parts.append(text)
            if self._within_partial_line or '\n' in text:
                self._write_text_parts()

    def _raw_write(self, string):
        fwrite(self.outfile, string)

    def _write_status(self, status):
        if not self.strip:
            status = status.rstrip().expandtabs()
            width = self.width or get_terminal_width()
            if width and len(status) > width:
                min_width = 10
                if len(status) >= min_width:
                    ellipsis = ' ... '
                    room = width - len(ellipsis)
                    pre_room = (room * 3) // 4
                    post_room = room - pre_room
                    status = status[:pre_room] + ellipsis + status[-post_room:]
                status = status[:width]
            padded_status = status.ljust(len(self._last_status))
            if padded_status:
                self._raw_write(padded_status + '\r')
            self._last_status = status

    def _erase_status(self):
        if self._last_status:
            self._raw_write(' ' * len(self._last_status) + '\r')
            self._last_status = ''

    def _clear_context(self):
        self._context_lines = []
        self._display_level = 0

    def _set_context(self, level, context):
        if self._display_level > level:
            self._display_level = level
        del self._context_lines[level + 1:]
        while level >= len(self._context_lines):
            self._context_lines.append('')
        self._context_lines[level] = context
        lines = [s.rstrip() for s in self._context_lines]
        lines = [line for line in lines if line]
        self._write_status('  '.join(lines))

    def _show_context(self):
        self._erase_status()
        end_level = len(self._context_lines)
        for level in range(self._display_level, end_level):
            self._raw_write(self._context_lines[level])
        self._display_level = end_level

    def _write_in_context(self, s):
            self._show_context()
            self._raw_write(s)

    def _write_complete_line(self, line):
        """Write a complete line (exactly one newline; must be at the end).
        """
        if self._heading_regex and re.search(self._heading_regex, line):
            self._clear_context()
        for level, regex in enumerate(self._regexes):
            if regex and re.search(regex, line):
                self._set_context(level, line)
                break
        else:
            self._write_in_context(line)

    def _write_line(self, line):
        """Write a single line (with or without a newline at the end).

        line contains at most one newline; if present, it must be at the end.
        line must not be the empty string.
        """
        has_newline = line.endswith('\n')
        is_complete_line = has_newline and not self._within_partial_line
        if is_complete_line:
            if self._num_lines_to_skip == 0:
                for count, regex in self._count_skip_regexes:
                    if regex and re.search(regex, line):
                        self._num_lines_to_skip = count
                        break
            if self._num_lines_to_skip > 0:
                self._num_lines_to_skip -= 1
            else:
                self._write_complete_line(line)
        else:
            self._write_in_context(line)
            self._within_partial_line = not has_newline

    def _write_text_parts(self, flush=False):
        if self._text_parts:
            joined_text = ''.join(self._text_parts)
            self._text_parts = []
            for line in joined_text.splitlines(True):
                if flush or self._within_partial_line or line.endswith('\n'):
                    self._write_line(line)
                else:
                    # Only the final line may lack a '\n'.
                    # Save this partial line for later.
                    self._text_parts.append(line)


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
                        metavar=('LEVEL', 'REGEX'),
                        help="""append "CONTEXT" regular expression for given
                        LEVEL; zero is highest-order level""")
    parser.add_argument('--heading-regex',
                        action='append',
                        dest='heading_regexes',
                        default=[],
                        metavar='HEADING_REGEX',
                        help='append a "HEADING" regular expression')
    parser.add_argument('--skip-regex',
                        action='append',
                        dest='count_skip_regexes',
                        nargs=2,
                        default=[],
                        metavar=('COUNT', 'SKIP_REGEX'),
                        help="""append a COUNT and a "SKIP" regular expression;
                        when the input line matches SKIP_REGEX, COUNT lines
                        will be skipped (COUNT includes the matching line)""")
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
    parser.add_argument('--width',
                        type=int,
                        dest='width',
                        default=0,
                        help="""width of terminal for truncating status lines
                        (0 ==> detect terminal width automatically)""")
    parser.add_argument('--encoding',
                        dest='encoding',
                        default='utf-8',
                        help="""encoding to use for all files (defaults to
                        utf-8)""")
    parser.add_argument('files',
                        nargs='*',
                        metavar='OUTFILE',
                        help="""an unmodified copy of stdin is written to each
                        output file""")
    parser.add_argument('--partial-line-timeout',
                        type=float,
                        dest='partial_line_timeout',
                        default=2.0,
                        help="""seconds to wait for remainder of line to arrive
                        before flushing (defaults to 2.0; 0 to disable)""")

    args = parser.parse_args()
    track_terminal_width()

    progress = Progress()
    for level, regex in args.level_regexes:
        try:
            level = int(level)
        except ValueError:
            parser.error('invalid LEVEL %s' % repr(level))
        progress.append_level_regex(int(level), regex)
    for regex in args.regexes:
        progress.append_level_regex(DEFAULT_LEVEL, regex)
    for regex in args.heading_regexes:
        progress.append_heading_regex(regex)
    for count_str, regex in args.count_skip_regexes:
        try:
            count = int(count_str)
            if count <= 0:
                raise ValueError()
        except ValueError:
            parser.error('argument --skip-regex: invalid COUNT %s' % count_str)
        progress.append_count_skip_regex(count, regex)
    if args.strip is None:
        progress.strip = not os.isatty(sys.stdout.fileno())
    else:
        progress.strip = args.strip
    progress.width = args.width
    progress.outfile = stdout_writer(args.encoding)
    decoder = codecs.getincrementaldecoder(args.encoding)()
    ditto_files = []
    mode = ('a' if args.append else 'w') + 'b'

    def read_into_queue(input_io, input_queue):
        block_size = 8192
        while True:
            raw_bytes = input_io.read(block_size)
            input_queue.put(raw_bytes)
            if not raw_bytes:
                break

    stdin = io.open(0, 'rb', closefd=False, buffering=0)
    stdin_queue = queue.Queue(10)
    t = threading.Thread(target=read_into_queue, args=(stdin, stdin_queue))
    t.daemon = True
    t.start()

    try:
        for name in args.files:
            ditto_files.append(io.open(name, mode))

        while True:
            if progress.have_unwritten_data:
                timeout = args.partial_line_timeout
                if timeout <= 0.0:
                    timeout = None
            else:
                timeout = None
            try:
                raw_bytes = stdin_queue.get(timeout=timeout)
            except queue.Empty:
                progress.flush()
            else:
                if not raw_bytes:
                    break
                for f in ditto_files:
                    fwrite(f, raw_bytes)
                progress.write(decoder.decode(raw_bytes))

        progress.write(decoder.decode(bytes(b''), final=True))

    finally:
        progress.close()
        for f in ditto_files:
            f.close()
        t.join()


def main():
    try:
        inner_main()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
