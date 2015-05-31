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

    def check(self, input_str, expected_output_str):
        tee = ptee.Tee()
        tee.regex = r'^status'
        tee.heading_regex = r'^heading'
        tee.outfile = StringIO()
        input_str = self.fixup_str(input_str)
        with closing(tee):
            tee.drain(StringIO(input_str))
        expected_output_str = self.fixup_str(expected_output_str)
        self.assertEqual(tee.outfile.getvalue(), expected_output_str)

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
                   status  #4\a\n
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
                   heading line\a\n
                   status #1\a
                   status longer #2\a\n
                   spaces      $
                   status #2\a\n
                   line 3
                   """)


if __name__ == '__main__':
    unittest.main()
