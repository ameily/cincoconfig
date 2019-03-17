#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import pytest
from cincoconfig.fields import ListField, ListFieldWrapper, IntField


class MockConfig:

    def __init__(self):
        self._data = {}


class TestListFieldWrapper:

    def test_create(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        assert wrap._items == [1, 2, 3]

    def test_len(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        assert len(wrap) == 3

    def test_eq(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        assert wrap == [1, 2, 3]

    def test_append(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap.append('4')
        assert wrap._items == [1, 2, 3, 4]

    def test_add(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap2 = wrap + [4, 5]
        assert wrap2 == [1, 2, 3, 4, 5]

    def test_iadd(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap += [4, 5]
        assert wrap._items == [1, 2, 3, 4, 5]

    def test_getitem(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        assert wrap[1] == 2

    def test_getitem_error(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        with pytest.raises(IndexError):
            _ = wrap[4]

    def test_setitem(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap[1] = '5'
        assert wrap._items == [1, 5, 3]

    def test_clear(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap.clear()
        assert wrap._items == []

    def test_copy(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap2 = wrap.copy()
        assert wrap._items == wrap2._items
        assert type(wrap.field) is type(wrap2.field)
        assert wrap.cfg is wrap2.cfg

    def test_count(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        assert wrap.count(2) == 1

    def test_index(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        assert wrap.index(3) == 2

    def test_insert(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap.insert(1, '6')
        assert wrap._items == [1, 6, 2, 3]

    def test_pop_none(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        val = wrap.pop()
        assert val == 3
        assert wrap._items == [1, 2]

    def test_pop_index(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        val = wrap.pop(1)
        assert val == 2
        assert wrap._items == [1, 3]

    def test_remove(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap.remove(2)
        assert wrap._items == [1, 3]

    def test_reverse(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap.reverse()
        assert wrap._items == [3, 2, 1]

    def test_sort(self):
        wrap = ListFieldWrapper(MockConfig(), IntField, 1, 2, '3')
        wrap.sort(reverse=True)
        assert wrap._items == [3, 2, 1]
