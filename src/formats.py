# pylint: disable=missing-docstring,invalid-name

from abc import ABC, abstractmethod
from datetime import datetime
from enum import IntEnum
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


class ParseError(IntEnum):
    """
    Class for handling parser error types.
    """
    NONE = 0
    SIGMA = 1
    PSAT = 2
    PZERO = 3
    FIT = 4


errm = {
    ParseError.NONE: 'XXX',
    ParseError.SIGMA: 'sigma/mu > 10%',
    ParseError.PSAT: 'pulse saturated',
    ParseError.PZERO: 'ADC value at 0',
    ParseError.FIT: 'fit error',
}


class DataFormatError(Exception):
    """
    General data format error class.
    Inherits from Exception errors.
    """
    pass


class DataTypeError(DataFormatError):
    """
    Raises an error if there is an invalid data type.
    Inherits from DataFormatError.
    """
    def __init__(self, version):
        message = 'invalid datatype in dataformat version: {}'.format(version)
        super().__init__(message)


class DataParseError(DataFormatError):
    """
    Raises an error if there is a problem parsing the data.
    Inherits from DataFormatError.
    """
    def __init__(self, data):
        message = 'error parsing raw data: {}'.format(data)
        super().__init__(message)


class DataFormat(ABC):
    """
    General data formatting class.
    """
    datatypes = [
        'TEXT',
        'NUMERIC',
        'INTEGER',
        'REAL',
        'BLOB',
    ]

    @classmethod
    def verify(cls, structure):
        """
        :param XXX structure:
        """
        return all(v in cls.datatypes for v in structure.values())

    @abstractmethod
    def parser(self, raw):
        """
        :param XXX raw:
        """
        pass


class DataFormat_v1(DataFormat):
    """
    Database formatting for ADC boards.
    Inherits from DataFormat.
    """
    structure = {
        'serial': 'TEXT',
        'id': 'TEXT',
        'offset': 'INTEGER',
        'nstep': 'INTEGER',
        'nstep_event': 'INTEGER',
        'nstep_data': 'INTEGER',
        'nsample': 'INTEGER',
        'pedes': 'TEXT',
        'gains': 'TEXT',
        'location': 'TEXT',
        'history': 'TEXT',
        'comment': 'TEXT',
        'status': 'TEXT',
        'files': 'TEXT',
        'rack': 'TEXT',
        'crate': 'TEXT',
        'slot': 'TEXT',
        'detector': 'TEXT',
    }

    def parser(self, raw, callback=None):
        """
        Parser for ADC board data.
        :param XXX raw: Raw data to be processed.
        :param XXX callback:
        """
        entry = {}

        files = [''] * 4
        pedes = np.zeros((64, 2))
        gains = np.zeros((64, 2))

        magic = '-' * 32

        with open(raw, 'r') as fp, open(os.devnull, 'w') as fn:
            metadata = {}

            while (keyval := read_config_line(fp))[0] != magic:
                metadata[keyval[0]] = keyval[1]

            entry['serial'] = metadata['BOARDID']
            entry['offset'] = int(metadata['CHANNELMIN'])
            entry['nstep'] = int(metadata['NUMBEROFSTEPS'])
            entry['nstep_event'] = int(metadata['EVENTSPERSTEP'])
            entry['nstep_data'] = int(metadata['DACPERSTEP'])
            entry['nsample'] = int(metadata['NSAMPLES'])

            offset = entry['offset']
            nstep = entry['nstep']
            ntrial = entry['nstep_event']
            nsample = entry['nsample']

            group = offset // 16

            files[group] = raw

            front = group * nsample
            back = (3 - group) * nsample

            entry['files'] = ', '.join(files)

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

                if callback is not None:
                    callback(i * 50 / nstep)

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

            errc = np.zeros((16, nstep), dtype=np.int32)

            for i in range(nstep):
                for j in range(0, 16):
                    if np.any(rels[i,j,:] > 0.1):
                        err = ParseError.SIGMA
                        display_fit_error(errm[err])
                        errc[j,i] = int(err)
                        continue

                    if np.any(sigma == 0) and np.any(mean == 16384):
                        err = ParseError.PSAT
                        display_fit_error(errm[err])
                        errc[j,i] = int(err)
                        continue

                    if np.any(sigma == 0) and np.any(mean == 0):
                        err = ParseError.PZERO
                        display_fit_error(errm[err])
                        errc[j,i] = int(err)
                        continue

                    try:
                        popt, pcov = fit_signal(mean, sigma, nsample, i, j,
                            method='dogbox')
                        xmin = fmin(min_form, 5, args=tuple(popt))

                        y[j][i] = powerlaw_doubleexp(xmin, *popt)
                    except (ValueError, np.linalg.LinAlgError):
                        err = ParseError.FIT
                        display_fit_error(errm[err])
                        errc[j,i] = int(err)
                        pass
                    except RuntimeError:
                        pass

                if callback is not None:
                    callback(50 + (i * 50 / nstep))

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

            i_min = offset
            i_max = offset + 16

            pedes[i_min:i_max,0] = pars[:,0]
            pedes[i_min:i_max,1] = errs[:,0]
            gains[i_min:i_max,0] = pars[:,1]
            gains[i_min:i_max,1] = errs[:,1]

            entry['pedes'] = np.array_repr(pedes)
            entry['gains'] = np.array_repr(gains)

        timestamp = datetime.now().strftime('%y%m%d-%H:%M:%S')

        errors = [
            '[C {}/P {}] error: {}'.format(
                i_min + idx[0], idx[1], errm[ParseError(e)]
            )
            for idx, e in np.ndenumerate(errc)
            if ParseError(e) is not ParseError.NONE
        ]

        entry['history'] = 'UPDATE: ({}:{}) [{}]'.format(
            i_min, i_max - 1, timestamp)
        entry['comment'] = '; '.join(errors)
        entry['status'] = '??'
        entry['rack'] = ''
        entry['crate'] = ''
        entry['slot'] = ''
        entry['detector'] = ''

        return entry, mean, sigma, y, pars, errs


class DataFormat_v2(DataFormat):
    """
    Database formatting for XMIT boards. Does not parse data.
    Inherits from DataFormat.
    """
    structure = {
        'serial': 'TEXT',
        'id': 'TEXT',
        'location': 'TEXT',
        'history': 'TEXT',
        'comment': 'TEXT',
        'status': 'TEXT',
        'files': 'TEXT',
        'rack': 'TEXT',
        'crate': 'TEXT',
        'slot': 'TEXT',
        'detector': 'TEXT',
    }

    def parser(self, raw):
        """
        Parser for XMIT board data. No data is processed.
        """
        pass


factory = {
    'adc': DataFormat_v1,
    'xmit': DataFormat_v2,
    'v1': DataFormat_v1,
    'v2': DataFormat_v2,
}
