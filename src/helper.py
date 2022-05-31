# pylint: disable=missing-docstring,invalid-name

import operator

from squash import Squash

import formats


class SquashHelper:
    """
    Creates a helper object for interfacing between the tkinter GUI and the
    Squash database control object.
    """
    squash = None
    path = None
    table = None

    def __init__(self, path, table='data', version='auto'):
        """
        Initializes a SquashHelper object that interfaces with a Squash
        database control object.
        :param str path: The system path to the SQLite database.
        :param str table: The data table within the database. 
        :param str version: The database version. ???
        """
        self.squash = Squash(path)
        self.path = path
        self.table = table

        def _set(self, version):
            """
            Sets the version.
            :param str version: The database version. ???
            """
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
        """
        Closes the database connection and resets variables.
        """
        self.squash.close()

        self.squash = None
        self.path = None
        self.table = None
        self.version = None
        self.object = None

    def check(self, path, table='data'):
        """
        Checks the version of the database. ???
        :param str path:  The system path to the SQLite database.
        :param str table: The data table within the database.
        """
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
        """
        ???
        """
        structure = self.object.structure

        if not formats.DataFormat.verify(structure):
            raise formats.DataTypeError(self.version)

        self.squash.insert_table(structure, self.table)

    def label(self, data):
        """
        ???
        """
        structure = self.object.structure

        if not formats.DataFormat.verify(structure):
            raise formats.DataTypeError(self.version)

        return { v: data[i] for i, v in enumerate(structure.keys()) }

    def parse(self, raw, **kwargs):
        """
        Parses inputs.
        :param raw: Raw input data to be parsed.
        """
        return self.object.parser(raw, **kwargs)

    def insert(self, columns, data):
        """
        :param ??? columns:
        :param ??? data:
        """
        return self.squash.insert_entry(columns, data, self.table)

    def update(self, columns, data, condition):
        """
        Updates a database entry.
        :param list/tuple columns: List of data categories to insert.
        :param list data: List of datapoints to insert, corresponding to categories.
        :param str condition: Conditional statements for the query. ???
        """
        return self.squash.update_entry(columns, data, condition, self.table)

    def select(self, condition=''):
        """
        :param str condition: Conditional statements for the selection query. ???
        """
        return self.squash.select_entry('*', condition, self.table)
