# pylint: disable=missing-docstring,invalid-name

import operator

from squash import Squash

import formats


class SquashHelper:
    squash = None
    path = None
    table = None
    version = None

    def __init__(self, path, table='data', version='auto'):
        self.squash = Squash(path)
        self.path = path
        self.table = table
        self.version = version
        self.object = formats.factory[version]()

    def close(self):
        self.squash.close()

        self.squash = None
        self.path = None
        self.table = None
        self.version = None
        self.object = None

    def create(self):
        structure = self.object.structure

        if not formats.DataFormat.verify(structure):
            raise formats.DataTypeError(self.version)

        self.squash.insert_table(structure, self.table)

    def insert(self, raw):
        keys, values = zip(*self.object.parser(raw).items())
        self.squash.insert_entry(keys, values, self.table)

    def select(self, column='*', condition=''):
        return self.squash.select_entry(column, condition, self.table)

    def update(self, columns, data, condition):
        return self.squash.update_entry(columns, data, condition, self.table)

    def append(self, columns, data, condition):
        entry = [self.select(c, condition)[0][0] for c in columns]

        if not all(isinstance(v, str) for v in entry):
            raise TypeError('append operation is supported only for strings')

        values = list(map(operator.add, entry, map(str, data)))
        self.update(columns, values, condition)
