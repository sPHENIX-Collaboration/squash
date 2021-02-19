# pylint: disable=missing-docstring,invalid-name

from abc import ABC, abstractmethod


class DataFormatError(Exception):
    pass


class DataTypeError(DataFormatError):
    def __init__(self, version):
        message = 'invalid datatype in dataformat version: {}'.format(version)
        super().__init__(message)


class DataParseError(DataFormatError):
    def __init__(self, data):
        message = 'error parsing raw data: {}'.format(data)
        super().__init__(message)


class DataFormat(ABC):
    datatypes = [
        'TEXT',
        'NUMERIC',
        'INTEGER',
        'REAL',
        'BLOB',
    ]

    @classmethod
    def verify(cls, structure):
        return all(v in cls.datatypes for v in structure.values())

    @abstractmethod
    def parser(self, raw):
        pass


class DataFormat_v1(DataFormat):
    structure = {
        'label': 'TEXT',
        'val0': 'INTEGER',
        'val1': 'INTEGER',
        'val2': 'INTEGER',
    }

    def parser(self, raw):
        data = [raw]

        with open(raw, 'r') as fp:
            for _ in range(3):
                line = fp.readline().strip()
                data.append(int(line))

        return data


factory = {
    'auto': DataFormat_v1,
    'v1': DataFormat_v1,
}
