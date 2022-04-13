# pylint: disable=missing-docstring,invalid-name

import sqlite3


class SquashError(Exception):
    pass


class SquashConnectionError(SquashError):
    def __init__(self):
        message = 'no database connection'
        super().__init__(message)


class SquashEmptyError(SquashError):
    def __init__(self):
        message = 'no tables in database'
        super().__init__(message)


class Squash:
    connection = None
    path = None

    def __init__(self, path):
        self.open(path)

    def __str__(self):
        return 'squash: connected to {}'.format(self.path.__str__())

    class Decorators:
        @classmethod
        def check_connection(cls, f):
            def wrapper(self, *args, **kwargs):
                if self.connection is None or self.path is None:
                    raise SquashConnectionError

                return f(self, *args, **kwargs)

            return wrapper

        @classmethod
        def check_empty(cls, f):
            def wrapper(self, *args, **kwargs):
                cursor = self.connection.cursor()

                query = 'SELECT name FROM sqlite_master'
                cursor.execute(query)

                tables = cursor.fetchall()
                if not tables:
                    raise SquashEmptyError

                return f(self, *args, **kwargs)

            return wrapper

    def open(self, path):
        try:
            self.connection = sqlite3.connect(path)
            self.path = path
        except sqlite3.Error as e:
            print(e)

    @Decorators.check_connection
    def close(self):
        self.connection.close()

        self.connection = None
        self.path = None

    @Decorators.check_connection
    def write(self):
        self.connection.commit()

    @Decorators.check_connection
    def query(self, command):
        cursor = self.connection.cursor()

        cursor.execute(command)

        self.write()

        return cursor.fetchall()

    @Decorators.check_connection
    def insert_table(self, columns, table='data'):
        cursor = self.connection.cursor()

        fcolumns = ', '.join('{} {}'.format(k, v) for k, v in columns.items())
        query = 'CREATE TABLE {} ({})'.format(table, fcolumns)
        cursor.execute(query)

        self.write()

    @Decorators.check_connection
    @Decorators.check_empty
    def insert_entry(self, columns, data, table='data'):
        cursor = self.connection.cursor()

        fcolumns = ', '.join(columns)
        fdata = ', '.join(repr(d) for d in data)
        query = 'INSERT INTO {} ({}) VALUES ({})'.format(table, fcolumns, fdata)
        cursor.execute(query)

        self.write()

    @Decorators.check_connection
    @Decorators.check_empty
    def select_table(self, table='data'):
        cursor = self.connection.cursor()

        query = 'SELECT * FROM sqlite_master WHERE name LIKE {}'.format(table)
        cursor.execute(query)

        return cursor.fetchall()

    @Decorators.check_connection
    @Decorators.check_empty
    def select_entry(self, column, condition, table='data'):
        cursor = self.connection.cursor()

        query = 'SELECT {} FROM {} {}'.format(column, table, condition)
        cursor.execute(query)

        return cursor.fetchall()

    @Decorators.check_connection
    @Decorators.check_empty
    def update_entry(self, columns, data, condition, table='data'):
        cursor = self.connection.cursor()

        fupdate = ','.join(['{} = ?'.format(k) for k in columns])
        query = 'UPDATE {} SET {} {}'.format(table, fupdate, condition)
        cursor.execute(query, tuple(data))

        self.write()
