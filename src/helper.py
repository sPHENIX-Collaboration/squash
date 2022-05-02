# pylint: disable=missing-docstring,invalid-name

import operator

from squash import Squash

import formats


class SquashHelper:
    squash = None
    path = None
    table = None

    def __init__(self, path, table='data', version='auto'):
        self.squash = Squash(path)
        self.path = path
        self.table = table

        def _set(self, version):
            if version is None:
                self.version = None
                self.object = None
            else:
                self.version = version
                self.object = formats.factory[version]()

        if version is None:
            _set(self, None)
        elif version == 'auto':
            _set(self, self.check(self.path, self.table))
        else:
            _set(self, version)

    def close(self):
        self.squash.close()

        self.squash = None
        self.path = None
        self.table = None
        self.version = None
        self.object = None

    def check(self, path, table='data'):
        info = self.squash.query('pragma table_info({})'.format(table))

        versions = [
            k
            for k, v in formats.factory.items()
            if (
                len(info) == len(v.structure)
                and all(x[1] in v.structure for x in info)
            )
        ]

        if not versions:
            return None

        return versions[0]

    def create(self):
        structure = self.object.structure

        if not formats.DataFormat.verify(structure):
            raise formats.DataTypeError(self.version)

        self.squash.insert_table(structure, self.table)

    def label(self, data):
        structure = self.object.structure

        if not formats.DataFormat.verify(structure):
            raise formats.DataTypeError(self.version)

        return { v: data[i] for i, v in enumerate(structure.keys()) }

    def parse(self, raw, **kwargs):
        return self.object.parser(raw, **kwargs)

    def insert(self, columns, data):
        return self.squash.insert_entry(columns, data, self.table)

    def update(self, columns, data, condition):
        return self.squash.update_entry(columns, data, condition, self.table)

    def select(self, condition=''):
        return self.squash.select_entry('*', condition, self.table)
