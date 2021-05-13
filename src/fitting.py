import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from utils import (
    powerlaw_doubleexp,
    powerlaw_doubleexp_part0,
    powerlaw_doubleexp_part1,
)


def fit_signal(mean, sigma, nsamples, pulse, channel, **kwargs):
    print('pulse: {}, channel: {}'.format(pulse, channel))

    x = np.array(range(nsamples))
    y = mean[pulse,channel,:]
    w = sigma[pulse,channel,:]

    amax = np.amax(y)

    pval = [amax * 0.76, 3.5,    0.66,    0.96,    y[0], 0.56,    2.77]
    bmin = [        0.0, 0.0, -np.inf, -np.inf, -np.inf,  0.0, -np.inf]
    bmax = [       amax, 8.0,  np.inf,  np.inf,  np.inf,  1.0,  np.inf]

    popt, pcov = curve_fit(powerlaw_doubleexp, x, y, sigma=w, p0=pval,
        bounds=(bmin, bmax), **kwargs)

    # print(popt)
    # print(np.sqrt(np.diag(pcov)))

    # residuals = (powerlaw_doubleexp(x, *popt) - y) / y

    # print(np.sum(np.abs(residuals)) / nsamples)

    return popt, pcov


def overlay_fit(x, y, yerr, popt):
    lin = np.linspace(x[0], x[-1], len(x) * 100)

    fun = powerlaw_doubleexp(lin, *popt)
    fp0 = powerlaw_doubleexp_part0(lin, *popt)
    fp1 = powerlaw_doubleexp_part1(lin, *popt)

    fig = plt.figure()

    ax = fig.add_subplot(1, 1, 1)

    ax.errorbar(x, y, yerr=yerr, fmt='ro')

    plt.plot(lin, fp0, 'b')
    plt.plot(lin, fp1, 'y')
    plt.plot(lin, fun, 'g')

    plt.show()
