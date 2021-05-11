# pylint: disable=missing-docstring,invalid-name

from display import draw_graph, draw_histogram
from formats import factory

import matplotlib.pyplot as plt
import numpy as np


def analysis():
    data = [
        'dat/board001_Channel0to15_20210310_InjectCharge.dat',
        # 'dat/board001_Channel16to31_20210310_InjectCharge.dat',
        # 'dat/board001_Channel32to47_20210310_InjectCharge.dat',
        # 'dat/board001_Channel48to63_20210310_InjectCharge.dat',
        # 'dat/board0x69_Channel0to15_20210311_InjectCharge.dat',
        # 'dat/board0x69_Channel16to31_20210311_InjectCharge.dat',
        # 'dat/board0x69_Channel32to47_20210311_InjectCharge.dat',
        # 'dat/board0x69_Channel48to63_20210311_InjectCharge.dat',
        # 'dat/board0x70_Channel0to15_20210311_InjectCharge.dat',
        # 'dat/board0x70_Channel16to31_20210311_InjectCharge.dat',
        # 'dat/board0x70_Channel32to47_20210311_InjectCharge.dat',
        # 'dat/board0x70_Channel48to63_20210311_InjectCharge.dat',
        # 'dat/board0x71_Channel0to15_20210310_InjectCharge.dat',
        # 'dat/board0x71_Channel16to31_20210310_InjectCharge.dat',
        # 'dat/board0x71_Channel32to47_20210310_InjectCharge.dat',
        # 'dat/board0x71_Channel48to63_20210310_InjectCharge.dat',
    ]

    ref = [
        'dat/board001_Channel0to15_20210310_NoCharge.dat',
        # 'dat/board001_Channel16to31_20210310_NoCharge.dat',
        # 'dat/board001_Channel32to47_20210310_NoCharge.dat',
        # 'dat/board001_Channel48to63_20210310_NoCharge.dat',
        # 'dat/board0x69_Channel0to15_20210311_NoCharge.dat',
        # 'dat/board0x69_Channel16to31_20210311_NoCharge.dat',
        # 'dat/board0x69_Channel32to47_20210311_NoCharge.dat',
        # 'dat/board0x69_Channel48to63_20210311_NoCharge.dat',
        # 'dat/board0x70_Channel0to15_20210311_NoCharge.dat',
        # 'dat/board0x70_Channel16to31_20210311_NoCharge.dat',
        # 'dat/board0x70_Channel32to47_20210311_NoCharge.dat',
        # 'dat/board0x70_Channel48to63_20210311_NoCharge.dat',
        # 'dat/board0x71_Channel0to15_20210310_NoCharge.dat',
        # 'dat/board0x71_Channel16to31_20210310_NoCharge.dat',
        # 'dat/board0x71_Channel32to47_20210310_NoCharge.dat',
        # 'dat/board0x71_Channel48to63_20210310_NoCharge.dat',
    ]

    squash = factory['auto']()

    # bases = []
    # gains = []

    # for group in zip(*[iter(data)] * 4):
    #     for f in group:
    #         _, _, _, _, coefs = squash.parser(f, output='signal')

    #         bases.append(coefs[:,0])
    #         gains.append(coefs[:,1])

    # np_bases = np.concatenate(bases)
    # np_gains = np.concatenate(gains)

    # # print(np_bases)
    # # print(np_gains)

    # # distribution of pedestals
    # draw_histogram(np_bases, 50, labels=('pedestal', 'counts'),
    #     xrange=(1300, 1800, 100), yrange=(0, 50, 5))

    # # distribution of gains
    # draw_histogram(np_gains, 25, labels=('gains', 'counts'),
    #     xrange=(90, 115, 5), yrange=(0, 100, 10))

    ###########################################################################

    bases = []
    gains = []

    for group in zip(*[iter(data)] * 1):
        bases.append([])
        gains.append([])

        for f in group:
            _, _, _, _, coefs = squash.parser(f, output='signal')

            # print(pars)
            # print(errs)

            bases[-1].extend(coefs[:,0])
            gains[-1].extend(coefs[:,1])

    fmt_str = ['board {}']
    fmt_data = [('001',), ('0x69',), ('0x70',), ('0x71',)]

    # y = np.array(bases)
    y = np.array(gains)

    # draw_graph(y, None, (1200, 1800, 100), 4, ('channel', 'pedestal'),
    #     fmt_str=fmt_str, fmt_data=fmt_data)
    draw_graph(y, None, (80, 120, 5), 4, ('channel', 'gain'),
        fmt_str=fmt_str, fmt_data=fmt_data)

    ###########################################################################

    # refstd = []

    # for group in zip(*[iter(ref)] * 4):
    #     refstd.append([])

    #     for f in group:
    #         raw = squash.parser(f, output='raw')

    #         for i in range(16):
    #             channel = raw[:,:,i,:].flatten()

    #             refstd[-1].append(np.std(channel).item())

    # y = np.array(refstd)

    # print(y)

    # fmt_str = ['board {}']
    # fmt_data = [('001',), ('0x69',), ('0x70',), ('0x71',)]

    # draw_graph(y, None, (0, 20, 2), 4, ('channel', 'std(pedestal)'),
    #     fmt_str=fmt_str, fmt_data=fmt_data)

    # # distribution of rms values for ref data
    # draw_histogram(np_refstd, 20, labels=('std(ADC)', 'counts'),
    #     xrange=(0, 20, 2), yrange=(0, 60, 10))

    # # example distribution for ref data (1 channel)
    # raw = squash.parser(ref[0], output='raw')

    # np_channel = raw[:,:,4,:].flatten()

    # draw_histogram(np_channel, 100, labels=('ADC', 'counts'),
    #     xrange=(1500, 1600, 20), yrange=(0, 32000, 4000))

    # # plot residuals
    # _, _, integral, quadsums, coefs = squash.parser(data[0], output='signal')

    # x = np.arange(0, integral.shape[-1], 1)
    # y = integral[0]
    # yerr = quadsums[0]

    # residuals = y - (coefs[0][0] + x * coefs[0][1])

    # print(residuals)

    # plt.figure()

    # axs = plt.gca()
    # axs.set_xlim(-0.5, 40)
    # axs.set_ylim(-50, 50)
    # axs.xaxis.set_ticks(range(0, 40, 4))
    # axs.yaxis.set_ticks(range(-50, 50, 10))
    # axs.set_xlabel('sample #')
    # axs.set_ylabel('residuals')

    # plt.errorbar(x, residuals, yerr=yerr, fmt='o')
    # plt.show()

    # mean, sigma, _, _, _ = squash.parser(f, output='signal')

    # disp_opts['yrange'] = (1500, 1600, 10)
    # disp_opts['interval'] = 4
    # disp_opts['labels'] = ('sample #', 'ADC value')

    # if c_null is True:
    #     disp_opts['fmt_str'] = ['channel {}']
    #     disp_opts['fmt_data'] = [list(zip(range(mean.shape[1])))]
    # else:
    #     disp_opts['fmt_str'] = ['pulse {}']
    #     disp_opts['fmt_data'] = [list(zip(range(mean.shape[0])))]

    # selection = p_slice, c_slice

    # draw_graph(mean[selection], sigma[selection], **disp_opts)


if __name__ == '__main__':
    analysis()
