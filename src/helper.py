# pylint: disable=missing-docstring,invalid-name

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
        self.squash.insert_entry(raw, self.object.parser)

    def select(self, column='*', condition=''):
        return self.squash.select_entry(self.table, column, condition)
