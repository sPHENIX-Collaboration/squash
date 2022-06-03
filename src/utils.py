# pylint: disable=missing-docstring,invalid-name

import numpy as np

from itertools import zip_longest
from scipy.optimize import curve_fit


def read_and_discard_lines(f, count):
    """
    Reads and discards a set number of lines of a file.
    :param file f: The file to read from.
    :param int count: The number of lines to read and discard.
    """
    for _ in range(count):
        f.readline()


def read_config_line(f):
    """
    Reads a colon-separated line of the provided input file and splits it into a list
    of values.
    :param file f: The file to read from.
    """
    return [x.strip() for x in f.readline().split(':')]


def split_dword(dword):
    """
    XXX
    :param XXX dword:
    """
    if isinstance(dword, str):
        dword = int(dword, 16)

    return dword & 0xFFFF, dword >> 16


def slice_from_string(text):
    """
    Slices a colon-separated string into individual elements.
    :param str text: Input string to slice.
    """
    if not text:
        return None

    fields = [int(x) for x in text.split(':')]

    if len(fields) == 1:
        return slice(fields[0], fields[0] + 1, 1)

    if len(fields) == 2:
        return slice(fields[0], fields[1], 1)

    if len(fields) == 3:
        return slice(fields[0], fields[1], fields[2])


def linear(x, a, b):
    """
    Linear fit function.
    """
    return a + b * x


def powerlaw_doubleexp_part0(x, a, b, c, d, e, f, g):
    """
    Power law fit function.
    """
    pedestal = e
    signal = e + a * np.power(x - b, c) * (
        ((1. - f) / np.power(d, c) * np.exp(c)) * np.exp((b - x) * c / d)
    )

    return np.where(x < b, pedestal, signal)


def powerlaw_doubleexp_part1(x, a, b, c, d, e, f, g):
    """
    Power law fit function.
    """
    pedestal = e
    signal = e + a * np.power(x - b, c) * (
        (f / np.power(g, c) * np.exp(c)) * np.exp((b - x) * c / g)
    )

    return np.where(x < b, pedestal, signal)


def powerlaw_doubleexp(x, a, b, c, d, e, f, g):
    """
    Power law fit function.
    """
    pedestal = e
    signal = e + a * np.power(x - b, c) * (
        ((1. - f) / np.power(d, c) * np.exp(c)) * np.exp((b - x) * c / d)
        + (f / np.power(g, c) * np.exp(c)) * np.exp((b - x) * c / g)
    )

    return np.where(x < b, pedestal, signal)


def powerlaw_singleexp(x, a, b, c, d, e):
    """
    Power law fit function.
    """
    pedestal = e
    signal = e + a * np.power(x - b, c) * np.exp((b - x) * d)

    return np.where(x < b, pedestal, signal)
