# pylint: disable=missing-docstring,invalid-name

import numpy as np

from itertools import zip_longest
from scipy.optimize import curve_fit


def read_and_discard_lines(f, count):
    for _ in range(count):
        f.readline()


def read_config_line(f):
    return f.readline().strip().split(' ')[-1]


def split_dword(dword):
    if isinstance(dword, str):
        dword = int(dword, 16)

    return dword & 0xFFFF, dword >> 16


def index_slice_from_string(text):
    return slice(int(text), int(text) + 1)


def slice_from_string(text):
    if text and ':' not in text:
        return index_slice_from_string(text)

    string_to_field = {
        True: int,
        False: lambda x: None,
    }

    args = list(zip(*zip_longest(text.split(':'), range(3))))[0]

    return slice(*[string_to_field[bool(x)](x) for x in args])


def linear(x, a, b):
    return a + b * x


def powerlaw_doubleexp_part0(x, a, b, c, d, e, f, g):
    pedestal = e
    signal = e + a * np.power(x - b, c) * (
        ((1. - f) / np.power(d, c) * np.exp(c)) * np.exp((b - x) * c / d)
    )

    return np.where(x < b, pedestal, signal)


def powerlaw_doubleexp_part1(x, a, b, c, d, e, f, g):
    pedestal = e
    signal = e + a * np.power(x - b, c) * (
        (f / np.power(g, c) * np.exp(c)) * np.exp((b - x) * c / g)
    )

    return np.where(x < b, pedestal, signal)


def powerlaw_doubleexp(x, a, b, c, d, e, f, g):
    pedestal = e
    signal = e + a * np.power(x - b, c) * (
        ((1. - f) / np.power(d, c) * np.exp(c)) * np.exp((b - x) * c / d)
        + (f / np.power(g, c) * np.exp(c)) * np.exp((b - x) * c / g)
    )

    return np.where(x < b, pedestal, signal)


def powerlaw_singleexp(x, a, b, c, d, e):
    pedestal = e
    signal = e + a * np.power(x - b, c) * np.exp((b - x) * d)

    return np.where(x < b, pedestal, signal)
