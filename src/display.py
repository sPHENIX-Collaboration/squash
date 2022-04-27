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
    xscale=(0, 1),
    info=[0.08, 0.87, 0.08, 'left'],
    layout=None,
    canvas=(1.25, 1.05),
    margins=(0.6, 0.1, 0.1, 0.4),
    fontsizes=(6, 6, 6),
    fmt_str=None,
    fmt_data=None,
    output=True,
):
    x = xscale[0] + np.arange(0, vals.shape[-1], 1) * xscale[1]
    y = vals.squeeze()
    yerr = errs.squeeze() if errs is not None else [None] * vals.shape[-1]

    if y.ndim == 1:
        y = np.expand_dims(y, axis=0)

    if layout is None:
        rows = int(math.sqrt(y.shape[0]))
        cols = math.ceil(y.shape[0] / rows)
    else:
        cols, rows = dims

    fig = plt.figure()

    plotw = canvas[0] * cols
    ploth = canvas[1] * rows

    figw = plotw + margins[0] + margins[1]
    figh = ploth + margins[2] + margins[3]

    left = margins[0] / figw
    right = (figw - margins[1]) / figw
    top = (figh - margins[2]) / figh
    bottom = margins[3] / figh

    axs = fig.subplots(
        rows,
        cols,
        sharex=True,
        sharey=True,
        squeeze=False,
    )

    fig.set_size_inches((figw, figh))
    fig.subplots_adjust(left, bottom, right, top, wspace=0, hspace=0)

    for (i, j), ax in np.ndenumerate(axs):
        if i == rows - 1:
            ax.set_xlabel(labels[0], fontsize=fontsizes[0])
        if j == 0:
            ax.set_ylabel(labels[1], fontsize=fontsizes[0])

    for (i,), ax in np.ndenumerate(axs.ravel()):
        ax.set_ylim(top=yrange[1], bottom=yrange[0])

        ax.xaxis.set_ticks(range(x[0], x[-1], interval))
        ax.yaxis.set_ticks(range(*yrange))

        ax.tick_params(axis='both', which='major', labelsize=fontsizes[1])

        try:
            ax.errorbar(x, y[i], yerr=yerr[i], fmt='bo', markersize=1.0)

            if fmt_str is not None and fmt_data is not None:
                xinfo, yinfo, hinfo, xalign = info

                for f_str, f_data in zip(fmt_str, fmt_data):
                    ax.annotate(
                        f_str.format(*f_data[i]),
                        xy=(xinfo, yinfo),
                        xycoords='axes fraction',
                        fontsize=fontsizes[2],
                        ha=xalign,
                    )

                    yinfo -= hinfo
        except IndexError:
            pass

    if isinstance(output, str):
        fig.savefig(output)
        plt.close(fig)
    elif output is True:
        fig.show()
    elif output is None:
        return fig


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
