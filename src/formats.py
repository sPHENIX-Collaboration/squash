# pylint: disable=missing-docstring,invalid-name

from abc import ABC, abstractmethod

import numpy as np
from numpy.polynomial import Polynomial
from scipy.optimize import curve_fit

from utils import read_and_discard_lines, read_config_line, split_dword, linear


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
    def parser(self, raw, output='entry'):
        pass


class DataFormat_v1(DataFormat):
    structure = {
        'label': 'TEXT',
        'board': 'INTEGER',
        'offset': 'INTEGER',
        'nstep': 'INTEGER',
        'nstep_event': 'INTEGER',
        'nstep_data': 'INTEGER',
        'nsample': 'INTEGER',
        'coefs': 'TEXT',
    }

    def parser(self, raw, output='entry'):
        entry = [raw]

        with open(raw, 'r') as fp:
            entry.append(int(read_config_line(fp), 16))
            entry.append(int(read_config_line(fp)))

            read_and_discard_lines(fp, 4)

            for _ in range(4):
                entry.append(int(read_config_line(fp)))

            offset = entry[2]
            nstep = entry[3]
            ntrial = entry[4]
            nsample = entry[6]

            group = offset // 16

            front = group * nsample
            back = (3 - group) * nsample

            data = np.zeros((nstep, ntrial, 16, nsample))

            for i in range(nstep):
                for j in range(ntrial):
                    # read and discard 2 lines
                    read_and_discard_lines(fp, 2)

                    # read and discard lines (unused channels)
                    read_and_discard_lines(fp, front)

                    # read and process data array
                    raw = []

                    for _ in range(nsample):
                        line = fp.readline().strip()
                        raw.extend(filter(None, line.split(' ')))

                    channels = []

                    for group in zip(*[iter(raw)] * nsample):
                        channels.extend([[], []])

                        for dword in group:
                            low, high = split_dword(dword)

                            channels[-2].append(low)
                            channels[-1].append(high)

                    data[i, j] = channels

                    # read and discard lines (16 unused channels)
                    read_and_discard_lines(fp, back)

                    # read and discard 2 lines (unused, empty)
                    read_and_discard_lines(fp, 2)

            if output == 'raw':
                return data

            print(data.shape)
            data = data[:,:100,:,:]
            print(data.shape)

            mean = np.mean(data, axis=1)
            sigma = np.std(data, axis=1)

            integral = np.sum(mean, axis=-1).transpose() / nsample
            quadsums = np.sqrt(np.sum(np.square(sigma), axis=-1)).transpose() / nsample

            x = np.arange(0, integral.shape[-1], 1)
            w = 1.0 / quadsums

            try:
                coefs = np.stack(
                    [
                        Polynomial.fit(x, integral[i], 1, w=w[i]).convert().coef
                        for i in range(integral.shape[0])
                    ]
                )
            except np.linalg.LinAlgError:
                coefs = np.zeros((integral.shape[0], 2))

            entry.append(str(coefs))

            if output == 'signal':
                return mean, sigma, integral, quadsums, coefs

        return entry


factory = {
    'auto': DataFormat_v1,
    'v1': DataFormat_v1,
}
