# pylint: disable=missing-docstring,invalid-name

import sqlite3


class SquashError(Exception):
    """
    Raises a general error.
    Inherits the error Exception class.
    """
    pass


class SquashConnectionError(SquashError):
    """
    If the SQLite database connection is not established or is lost, raises a
    connection error. 
    Inherits the SquashError class.
    """
    def __init__(self):
        message = 'no database connection'
        super().__init__(message)


class SquashEmptyError(SquashError):
    """
    If the accessed database is empty, raises an empty database error.
    Inherits the SquashError class.
    """
    def __init__(self):
        message = 'no tables in database'
        super().__init__(message)


class Squash:
    """
    Creates an object for handling board data and interfacing with the SQL
    database. Takes in a database file path on creation.
    """
    connection = None
    path = None

    def __init__(self, path):
        """
        Initializes a Squash object that interfaces with the board database.
        :param str path: The system path to the SQLite database.
        """
        self.open(path) # Takes in a database path and opens it

    def __str__(self):
        """
        Provides an output string for the Squash class.
        """
        return 'squash: connected to {}'.format(self.path.__str__())

    class Decorators:
        @classmethod
        def check_connection(cls, f):
            """
            Checks that the connection to the database is still established.
            Raises an error if the connection is lost.
            :param function f: The function to be decorated.
            """
            def wrapper(self, *args, **kwargs):
                if self.connection is None or self.path is None:
                    raise SquashConnectionError

                return f(self, *args, **kwargs)

            return wrapper

        @classmethod
        def check_empty(cls, f):
            """
            Checks that there is data to query. If not, raises an error.
            :param function f: The function to be decorated.
            """
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
        """
        Opens the connection to the SQLite database. Raises an error if the
        connection fails.
        :param str path: The system path to the SQLite database.
        """
        try:
            self.connection = sqlite3.connect(path)
            self.path = path
        except sqlite3.Error as e:
            print(e)

    @Decorators.check_connection
    def close(self):
        """
        Closes the connection to the SQLite database and resets the connection
        and path variables.
        """
        self.connection.close()

        self.connection = None
        self.path = None

    @Decorators.check_connection
    def write(self):
        """
        Commits data to the database.
        """
        self.connection.commit()
    
    
    # SQL Query Functions
    
    
    @Decorators.check_connection
    def query(self, command):
        """
        Queries the database and executes the provided SQLite command.
        :param str command: SQL command to execute.
        """
        cursor = self.connection.cursor()

        cursor.execute(command)

        self.write()

        return cursor.fetchall()

    @Decorators.check_connection
    def insert_table(self, columns, table='data'):
        """
        Creates a data table within the provided database. ???
        :param list/tuple columns: List of data categories to insert.
        :param str table: The name of the database that the table is added to.
        """
        cursor = self.connection.cursor()

        fcolumns = ', '.join('{} {}'.format(k, v) for k, v in columns.items())
        query = 'CREATE TABLE {} ({})'.format(table, fcolumns)
        cursor.execute(query)

        self.write()

    @Decorators.check_connection
    @Decorators.check_empty
    def insert_entry(self, columns, data, table='data'):
        """
        Inserts a row of data (as columns) into the database. ???
        :param list/tuple columns: List of data categories to insert.
        :param list/tuple data: List of data values to insert
        :param str table: The name of the database that data is added to.
        """
        cursor = self.connection.cursor()

        fcolumns = ', '.join(columns)
        fdata = ', '.join(repr(d) for d in data)
        query = 'INSERT INTO {} ({}) VALUES ({})'.format(table, fcolumns, fdata)
        cursor.execute(query)

        self.write()

    @Decorators.check_connection
    @Decorators.check_empty
    def select_table(self, table='data'):
        """
        Selects all data from the provided data table.
        :param str table: The name of the data table.
        """
        cursor = self.connection.cursor()

        query = 'SELECT * FROM sqlite_master WHERE name LIKE {}'.format(table)
        cursor.execute(query)

        return cursor.fetchall()

    @Decorators.check_connection
    @Decorators.check_empty
    def select_entry(self, column, condition, table='data'):
        """
        Selects data from the database that satisfies a particular condition. ???
        :param str column: The data type (column) that data is added under.
        :param str condition: Conditional statements for the query.
        :param str table: The name of the table to access data from.
        """
        cursor = self.connection.cursor()

        query = 'SELECT {} FROM {} {}'.format(column, table, condition)
        cursor.execute(query)

        return cursor.fetchall()

    @Decorators.check_connection
    @Decorators.check_empty
    def update_entry(self, columns, data, condition, table='data'):
        """
        Updates a database entry.
        :param list/tuple columns: List of data categories to insert.
        :param list data: List of datapoints to insert, corresponding to categories.
        :param str condition: Conditional statements for the query.
        :param str table: The name of the data table that is being updated.
        """
        cursor = self.connection.cursor()

        fupdate = ','.join(['{} = ?'.format(k) for k in columns])
        query = 'UPDATE {} SET {} {}'.format(table, fupdate, condition)
        cursor.execute(query, tuple(data))

        self.write()
