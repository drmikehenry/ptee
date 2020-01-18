#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)

import unittest
import ptee
import textwrap
from io import StringIO
from contextlib import closing


class TestTee(unittest.TestCase):
    def fixup_str(self, s):
        if s.startswith('\n'):
            s = s[1:]
        s = textwrap.dedent(s)
        s = s.replace('$', '')
        s = s.replace('\a\n', '\r')
        return s

    def raw_check(self, raw_input_strings, raw_expected_output_str):
        progress = ptee.Progress()
        progress.append_level_regex(1, r'^status')
        progress.append_heading_regex(r'^heading')
        progress.outfile = StringIO()
        with closing(progress):
            for input_str in raw_input_strings:
                for line in StringIO(input_str):
                    progress.write(line)
        self.assertEqual(progress.outfile.getvalue(), raw_expected_output_str)

    def check(self, input_str, expected_output_str):
        self.raw_check([self.fixup_str(input_str)],
                       self.fixup_str(expected_output_str))

    def test_empty(self):
        self.check('',
                   '')

    def test_spaces(self):
        self.check("""
                   line
                       $
                   """,
                   """
                   line
                       $
                   """)

    def test_empty_line(self):
        self.check('\n', '\n')

    def test_no_status(self):
        self.check("""
                   line #1
                   line #2
                   """,
                   """
                   line #1
                   line #2
                   """)

    def test_just_status(self):
        self.check("""
                   status #1
                   """,
                   """
                   status #1\a
                            \a
                   """)
        self.check("""
                   status #1
                   status #2
                   """,
                   """
                   status #1\a
                   status #2\a
                            \a
                   """)

    def test_simple(self):
        self.check("""
                   line 1
                   status #1
                   status longer #2
                   status #3
                   status  #4
                   line 2
                   line 3
                   """,
                   """
                   line 1
                   status #1\a
                   status longer #2\a
                   status #3       \a
                   status  #4\a
                             \a
                   status  #4
                   line 2
                   line 3
                   """)

    def test_heading(self):
        self.check("""
                   heading line
                   status #1
                   status longer #2
                   spaces      $
                   status #2
                   line 3
                   """,
                   """
                   heading line
                   status #1\a
                   status longer #2\a
                                   \a
                   status longer #2
                   spaces      $
                   status #2\a
                            \a
                   status #2
                   line 3
                   """)

    def test_parts(self):
        input_str = self.fixup_str(
            """
            status #1
            status #2
            """)
        output_str = self.fixup_str(
            """
            status #1\a
            status #2\a
                     \a
            """)
        parts = [input_str[i:i+3] for i in range(0, len(input_str), 3)]
        self.raw_check(parts, output_str)


if __name__ == '__main__':
    unittest.main()
