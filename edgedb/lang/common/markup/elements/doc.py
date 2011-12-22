##
# Copyright (c) 2011 Sprymix Inc.
# All rights reserved.
#
# See LICENSE for details.
##


import difflib

from semantix.utils.datastructures import Field, typed
from . import base


class DocMarkup(base.Markup, ns='doc'):
    pass


class Section(DocMarkup):
    title = Field(str, coerce=True)
    body = Field(base.MarkupList, coerce=True)


class Text(DocMarkup):
    text = Field(str)


class Diff(DocMarkup):
    lines = Field(typed.StrList, coerce=True)

    @classmethod
    def get_diff(cls, a, b, fromfile='', tofile='', fromfiledate='',
                  tofiledate='', n=10):

        lines = difflib.unified_diff(a, b, fromfile, tofile, fromfiledate, tofiledate, n)
        lines=[line.rstrip() for line in lines]

        if lines:
            return cls(lines=lines)
        else:
            return Text(text='No differences')


class ValueDiff(DocMarkup):
    before = Field(str)
    after = Field(str)
