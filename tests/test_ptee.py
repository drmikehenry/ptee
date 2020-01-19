#!/usr/bin/env python3
# coding=utf-8

from contextlib import closing
from io import StringIO
import textwrap

import ptee


def fixup_str(s):
    if s.startswith("\n"):
        s = s[1:]
    s = textwrap.dedent(s)
    s = s.replace("$", "")
    s = s.replace("\a\n", "\r")
    return s


def raw_check(raw_input_strings, raw_expected_output_str):
    progress = ptee.Progress()
    progress.append_level_regex(1, r"^status")
    progress.append_heading_regex(r"^heading")
    progress.outfile = StringIO()
    with closing(progress):
        for input_str in raw_input_strings:
            for line in StringIO(input_str):
                progress.write(line)
    assert progress.outfile.getvalue() == raw_expected_output_str


def check(input_str, expected_output_str):
    raw_check([fixup_str(input_str)], fixup_str(expected_output_str))


def test_empty():
    check("", "")


def test_spaces():
    check(
        """
               line
                   $
               """,
        """
               line
                   $
               """,
    )


def test_empty_line():
    check("\n", "\n")


def test_no_status():
    check(
        """
               line #1
               line #2
               """,
        """
               line #1
               line #2
               """,
    )


def test_just_status():
    check(
        """
               status #1
               """,
        """
               status #1\a
                        \a
               """,
    )
    check(
        """
               status #1
               status #2
               """,
        """
               status #1\a
               status #2\a
                        \a
               """,
    )


def test_simple():
    check(
        """
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
               """,
    )


def test_heading():
    check(
        """
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
               """,
    )


def test_parts():
    input_str = fixup_str(
        """
        status #1
        status #2
        """
    )
    output_str = fixup_str(
        """
        status #1\a
        status #2\a
                 \a
        """
    )
    parts = [input_str[i : i + 3] for i in range(0, len(input_str), 3)]
    raw_check(parts, output_str)
