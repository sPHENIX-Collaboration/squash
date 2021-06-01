# pylint: disable=missing-docstring,invalid-name

from abc import ABC, abstractmethod

import numpy as np
from numpy.polynomial import Polynomial
from scipy.optimize import curve_fit, fmin

from fitting import fit_signal
from utils import (
    read_and_discard_lines,
    read_config_line,
    split_dword,
    linear,
    powerlaw_doubleexp,
)


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

            mean = np.mean(data, axis=1)
            sigma = np.std(data, axis=1)

            x = np.arange(nstep)
            y = np.zeros((16, nstep))

            def min_form(x, *args):
                return -powerlaw_doubleexp(x, *args)

            for i in range(nstep):
                for j in range(0, 16):
                    try:
                        popt, pcov = fit_signal(mean, sigma, nsample, i, j,
                            method='dogbox')
                        xmin = fmin(min_form, 5, args=tuple(popt))

                        y[j][i] = powerlaw_doubleexp(xmin, *popt)
                    except ValueError:
                        # fit without errors (sigma = 0 if ADC is saturated)
                        popt, pcov = fit_signal(mean, None, nsample, i, j,
                            method='dogbox')
                        xmin = fmin(min_form, 5, args=tuple(popt))

                        y[j][i] = powerlaw_doubleexp(xmin, *popt)
                    except RuntimeError:
                        pass

            pval = [1500, 375]
            bmin = [ 500, 275]
            bmax = [2500, 475]

            pars = np.zeros((0, 2))
            errs = np.zeros((0, 2))

            for i in range(y.shape[0]):
                popt, pcov = curve_fit(linear, x[2:], y[i,2:], p0=pval,
                    bounds=(bmin, bmax))

                pars = np.vstack((pars, popt))
                errs = np.vstack((errs, np.sqrt(np.diag(pcov))))

            entry.append(str(pars) + str(errs))

            print(pars)

            if output == 'signal':
                return mean, sigma, y, pars, errs

        return entry


factory = {
    'auto': DataFormat_v1,
    'v1': DataFormat_v1,
}
