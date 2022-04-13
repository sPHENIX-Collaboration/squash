# pylint: disable=missing-docstring,invalid-name

from abc import ABC, abstractmethod
from datetime import datetime
import os
import sys

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
        'board': 'TEXT',
        'offset': 'INTEGER',
        'nstep': 'INTEGER',
        'nstep_event': 'INTEGER',
        'nstep_data': 'INTEGER',
        'nsample': 'INTEGER',
        'coefs': 'TEXT',
        'info': 'TEXT',
    }

    def parser(self, raw, output='entry'):
        entry = { 'label': raw, }

        with open(raw, 'r') as fp, open(os.devnull, 'w') as fn:
            entry['board'] = read_config_line(fp)
            entry['offset'] = int(read_config_line(fp))

            read_and_discard_lines(fp, 4)

            for key in ('nstep', 'nstep_event', 'nstep_data', 'nsample'):
                entry[key] = int(read_config_line(fp))

            offset = entry['offset']
            nstep = entry['nstep']
            ntrial = entry['nstep_event']
            nsample = entry['nsample']

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

                    # read and discard lines (unused channels)
                    read_and_discard_lines(fp, back)

                    # read and discard 2 lines (unused, empty)
                    read_and_discard_lines(fp, 2)

            if output == 'raw':
                return data

            mean = np.mean(data, axis=1)
            sigma = np.std(data, axis=1)

            rels = sigma / mean;

            x = np.arange(nstep)
            y = np.zeros((16, nstep))

            def min_form(x, *args):
                return -powerlaw_doubleexp(x, *args)

            def display_fit_error(message):
                print(' [!] ERROR: [pulse: {}, channel: {}]'.format(i, j))
                print('     {}'.format(message))

            sys_stdout = sys.stdout
            sys.stdout = fn

            for i in range(nstep):
                for j in range(0, 16):
                    if np.any(rels[i,j,:] > 0.1):
                        display_fit_error('sigma/mu > 10%')
                        continue

                    if np.any(sigma == 0) and np.any(mean == 16384):
                        display_fit_error('pulse saturated')
                        continue

                    if np.any(sigma == 0) and np.any(mean == 0):
                        display_fit_error('pulse at 0')
                        continue

                    try:
                        popt, pcov = fit_signal(mean, sigma, nsample, i, j,
                            method='dogbox')
                        xmin = fmin(min_form, 5, args=tuple(popt))

                        y[j][i] = powerlaw_doubleexp(xmin, *popt)
                    except ValueError:
                        display_fit_error('fit error (ValueError)')
                        pass
                    except np.linalg.LinAlgError:
                        display_fit_error('fit error (np.linalg.LinAlgError)')
                        pass
                    except RuntimeError:
                        pass

            sys.stdout = sys_stdout

            pval = [1500, 375]
            bmin = [ 500, 275]
            bmax = [2500, 475]

            pars = np.zeros((0, 2))
            errs = np.zeros((0, 2))

            for i in range(y.shape[0]):
                i_valid = y[i,2:] != 0

                if np.count_nonzero(i_valid) > 1:
                    x_valid = x[2:][i_valid]
                    y_valid = y[i,2:][i_valid]
                else:
                    x_valid = x[2:]
                    y_valid = y[i,2:]

                popt, pcov = curve_fit(linear, x_valid, y_valid, p0=pval,
                    bounds=(bmin, bmax))

                pars = np.vstack((pars, popt))
                errs = np.vstack((errs, np.sqrt(np.diag(pcov))))

            entry['coefs'] = np.array_repr(pars) + '###' + np.array_repr(errs)

            timestamp = datetime.today().strftime('%y%m%d-%H:%M:%S')
            entry['info'] = 'ENTRY ADDED: {}'.format(timestamp)

            print(pars)

            if output == 'signal':
                return mean, sigma, y, pars, errs

        return entry


factory = {
    'auto': DataFormat_v1,
    'v1': DataFormat_v1,
}
