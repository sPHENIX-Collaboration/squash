# pylint: disable=missing-docstring,invalid-name

import math

import matplotlib.pyplot as plt
import numpy as np


def draw_graph(
    vals,
    errs,
    yrange,
    interval,
    labels,
    info=[0.08, 0.84, 0.09],
    fmt_str=None,
    fmt_data=None,
    output=None,
):
    x = np.arange(0, vals.shape[-1], 1)
    y = vals.squeeze()
    yerr = errs.squeeze() if errs is not None else [None] * vals.shape[-1]

    if y.ndim == 1:
        y = np.expand_dims(y, axis=0)

    rows = int(math.sqrt(y.shape[0]))
    cols = math.ceil(y.shape[0] / rows)

    fig, axs = plt.subplots(
        rows,
        cols,
        sharex=True,
        sharey=True,
        figsize=(cols * 2.0, rows * 1.6),
        squeeze=False,
    )

    fig.subplots_adjust(wspace=0, hspace=0)

    for (i, j), ax in np.ndenumerate(axs):
        if i == rows - 1:
            ax.set_xlabel(labels[0], fontsize=9)
        if j == 0:
            ax.set_ylabel(labels[1], fontsize=9)

    for (i,), ax in np.ndenumerate(axs.ravel()):
        ax.set_ylim(top=yrange[1], bottom=yrange[0])

        ax.xaxis.set_ticks(range(x[0], x[-1], interval))
        ax.yaxis.set_ticks(range(*yrange))

        ax.tick_params(axis='both', which='major', labelsize=8)

        try:
            ax.errorbar(x, y[i], yerr=yerr[i], fmt='bo', markersize=1.0)

            if fmt_str is not None and fmt_data is not None:
                xinfo, yinfo, hinfo = info

                for f_str, f_data in zip(fmt_str, fmt_data):
                    ax.annotate(
                        f_str.format(*f_data[i]),
                        xy=(xinfo, yinfo),
                        xycoords='axes fraction',
                        fontsize=8,
                    )

                    yinfo -= hinfo
        except IndexError:
            pass

    if output is None:
        plt.show()
    else:
        plt.savefig(output)


def draw_histogram(vals, bins, labels, xrange, yrange):
    y, edges = np.histogram(vals, bins=bins, range=xrange[:2])
    x = (edges[:-1] + edges[1:]) / 2
    yerr = np.sqrt(y)

    plt.figure()

    axs = plt.gca()
    axs.set_xlim(xrange[:2])
    axs.set_ylim(yrange[:2])
    axs.xaxis.set_ticks(range(*xrange))
    axs.yaxis.set_ticks(range(*yrange))
    axs.set_xlabel(labels[0])
    axs.set_ylabel(labels[1])

    plt.errorbar(x, y, yerr=yerr, fmt='o')
    plt.show()
