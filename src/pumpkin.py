# pylint: disable=missing-docstring,invalid-name

from datetime import datetime
from enum import Enum
import os

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
from numpy import array
import tkinter as tk
from tkinter import filedialog, ttk

from display import draw_graph
from helper import SquashHelper
from utils import slice_from_string


class SIModes(Enum):
    NONE = 0
    OPEN = 1
    CREATE = 2
    ACTIVE = 3


class SIStates(Enum):
    NONE = 0
    INSERT = 1
    UPDATE = 2
    SELECT = 3


class SquashInterface:
    def __init__(self, master):
        self.master = master
        self.squash = None

        self.mode = SIModes.NONE
        self.state = SIStates.NONE

        self.results = None
        self.query = None
        self.index = None

        self.fig = None
        self.canvas = None

        self.init_frames()
        self.init_widgets()

        self.init_display()

    def init_frames(self):
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self.main = ttk.Frame(self.master)

        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)

        self.frame = ttk.Frame(self.main)

        self.frame.columnconfigure(1, weight=1)
        self.frame.columnconfigure(5, weight=1)
        self.frame.rowconfigure(6, weight=1)

        self.frame.columnconfigure(0, minsize=96)
        self.frame.columnconfigure(2, minsize=80)
        self.frame.columnconfigure(3, minsize=80)
        self.frame.columnconfigure(4, minsize=64)
        self.frame.columnconfigure(6, minsize=108)
        self.frame.rowconfigure(0, minsize=32)
        self.frame.rowconfigure(1, minsize=8)
        self.frame.rowconfigure(2, minsize=32)
        self.frame.rowconfigure(3, minsize=32)
        self.frame.rowconfigure(4, minsize=32)
        self.frame.rowconfigure(5, minsize=32)

        self.h_bar = ttk.Separator(self.frame, orient='horizontal')
        self.f_box = ttk.Frame(self.frame, relief='groove')

        self.f_box.columnconfigure(2, weight=1)
        self.f_box.rowconfigure(5, weight=1)

        self.f_box.columnconfigure(0, minsize=80)
        self.f_box.columnconfigure(1, minsize=200)

        self.p_bar = ttk.Progressbar(
            self.frame,
            orient='horizontal',
            mode='determinate',
        )

        self.anchor = ttk.Label(self.frame, width=6, anchor='center')

    def init_widgets(self):
        self.b_action = ttk.Button(self.frame, text='action', width=6)

        self.e_text = ttk.Entry(self.frame)
        self.e_text.bind('<Key-Return>', self.on_carriage_return)

        self.b_power = ttk.Button(self.frame, text='power', width=6)

        self.b_insert = ttk.Button(self.frame, text='insert', width=6)
        self.b_insert['command'] = self.on_click_insert
        self.b_update = ttk.Button(self.frame, text='update', width=6)
        self.b_update['command'] = self.on_click_update
        self.b_select = ttk.Button(self.frame, text='select', width=6)
        self.b_select['command'] = self.on_click_select

        self.l_serial = ttk.Label(self.f_box, text='serial #:', anchor='e', width=8)
        self.e_serial = ttk.Entry(self.f_box, width=12)
        self.l_qrcode = ttk.Label(self.f_box, text='board ID:', anchor='e', width=8)
        self.e_qrcode = ttk.Entry(self.f_box, width=12)

        self.l_location = ttk.Label(self.f_box, text='location:', anchor='e', width=8)
        self.e_location = ttk.Combobox(self.f_box, state=['readonly'], width=12)
        self.e_location['values'] = (
            '  UC Boulder',
            '  Nevis Labs (Columbia)',
            '  BNL (storage)',
            '  BNL (sPHENIX)',
        )
        self.e_location.set('  UC Boulder')

        self.l_comment = ttk.Label(self.f_box, text='comment:', anchor='e', width=8)
        self.e_comment = ttk.Entry(self.f_box, width=12)

        self.l_status = ttk.Label(self.f_box, text='status:', anchor='e', width=8)
        self.s_calib = ttk.Spinbox(self.f_box, state=['readonly'], width=12)
        self.s_calib['values'] = (' G/P: ?', ' G/P: P', ' G/P: F')
        self.s_token = ttk.Spinbox(self.f_box, state=['readonly'], width=12)
        self.s_token['values'] = (' TP: ?', ' TP: P', ' TP: F')

        self.b_record = ttk.Button(self.f_box, text='record', width=8)

        self.t_info = ttk.Treeview(self.f_box, selectmode='browse')
        self.t_info['columns'] = ['info']
        self.t_info.column('#0', width=96)
        self.t_info.heading('info', text='...')
        self.t_info.tag_configure('edit', foreground='red')
        self.t_info.tag_bind('edit', '<ButtonRelease-1>', self.on_edit_entry)

    def init_display(self):
        self.main.grid(column=0, row=0, sticky='nswe')
        self.frame.grid(column=0, row=0, padx=8, pady=4, sticky='nswe')

        self.b_power.grid(column=0, row=0)

        self.h_bar.grid(column=0, row=1, columnspan=7, rowspan=1, sticky='we')
        self.f_box.grid(
            column=1,
            row=2,
            columnspan=6,
            rowspan=5,
            padx=4,
            pady=4,
            sticky='nswe',
        )

        self.p_bar.grid(
            column=1, row=8, columnspan=6, rowspan=1, padx=8, sticky='we'
        )

        self.anchor.grid(column=0, row=8, padx=4, sticky='we')

        self.layout_display(self.mode, self.state)

    def clear_figure(self):
        if self.fig is None:
            return

        plt.close(self.fig)

        self.canvas.get_tk_widget().pack_forget()

        self.fig = None
        self.canvas = None

    def clear_action_group(self):
        self.e_text.delete(0, tk.END)
        self.e_text.grid_forget()
        self.b_action.grid_forget()

    def clear_record_group(self):
        self.e_serial.configure(state='normal')

        self.l_serial.grid_forget()
        self.e_serial.delete(0, tk.END)
        self.e_serial.grid_forget()
        self.l_qrcode.grid_forget()
        self.e_qrcode.delete(0, tk.END)
        self.e_qrcode.grid_forget()
        self.l_location.grid_forget()
        self.e_location.delete(0, tk.END)
        self.e_location.grid_forget()
        self.l_comment.grid_forget()
        self.e_comment.delete(0, tk.END)
        self.e_comment.grid_forget()
        self.l_status.grid_forget()
        self.s_calib.grid_forget()
        self.s_token.grid_forget()
        self.b_record.grid_forget()

    def clear_display(self, mode, state):
        self.reset_notification()

        if mode is SIModes.NONE:
            self.clear_action_group()

            self.b_insert.grid_forget()
            self.b_update.grid_forget()
            self.b_select.grid_forget()

        if mode is SIModes.ACTIVE:
            self.clear_action_group()

        if state is SIStates.INSERT:
            self.clear_action_group()

        if state is not SIStates.UPDATE:
            self.clear_figure()

        if self.state is SIStates.INSERT:
            self.clear_record_group()

        if self.state is SIStates.UPDATE:
            self.e_text.delete(0, tk.END)

        if self.state is SIStates.SELECT:
            self.e_text.delete(0, tk.END)

            self.t_info.delete(*self.t_info.get_children())
            self.t_info.grid_forget()

            self.clear_record_group()

            self.results = None
            self.query = None
            self.index = None

    def place_display(self, mode=None, state=None):
        if mode is SIModes.NONE:
            self.b_power['text'] = 'open'
            self.b_power['command'] = self.on_click_open

        if mode is SIModes.OPEN:
            self.e_text.grid(
                column=1, row=0, columnspan=5, rowspan=1, padx=8, sticky='we'
            )

            self.b_action['text'] = 'browse'
            self.b_action['command'] = self.on_click_browse
            self.b_action.grid(column=6, row=0, padx=4)

            self.e_text.focus_set()

        if mode is SIModes.ACTIVE:
            self.b_power['text'] = 'close'
            self.b_power['command'] = self.on_click_close

            self.b_insert.grid(column=0, row=2)
            self.b_update.grid(column=0, row=3)
            self.b_select.grid(column=0, row=4)

        if state is SIStates.INSERT:
            self.l_serial.grid(column=0, row=0, pady=2, sticky='e')
            self.e_serial.grid(column=1, row=0, pady=2, sticky='we')
            self.l_qrcode.grid(column=0, row=1, pady=2, sticky='e')
            self.e_qrcode.grid(column=1, row=1, pady=2, sticky='we')
            self.l_location.grid(column=0, row=2, pady=2, sticky='e')
            self.e_location.grid(column=1, row=2, pady=2, sticky='we')
            self.l_comment.grid(column=0, row=3, pady=2, sticky='e')
            self.e_comment.grid(column=1, row=3, pady=2, sticky='we')

            self.b_record['text'] = 'register'
            self.b_record['command'] = self.on_click_register
            self.b_record.grid(column=0, row=4, columnspan=2, rowspan=1, pady=4)

            self.e_serial.focus_set()

        if state is SIStates.UPDATE:
            self.e_text.grid(
                column=1, row=0, columnspan=5, rowspan=1, padx=4, sticky='we'
            )

            self.b_action['text'] = 'browse'
            self.b_action['command'] = self.on_click_browse
            self.b_action.grid(column=6, row=0, padx=4)

            self.e_text.focus_set()

        if state is SIStates.SELECT:
            self.e_text.grid(
                column=1, row=0, columnspan=5, rowspan=1, padx=4, sticky='we'
            )

            self.b_action['text'] = 'filter'
            self.b_action['command'] = self.on_carriage_return
            self.b_action.grid(column=6, row=0, padx=4)

            self.t_info.grid(
                column=0,
                row=5,
                columnspan=3,
                rowspan=1,
                padx=4,
                pady=4,
                sticky='nswe',
            )

            self.e_text.focus_set()

    def layout_display(self, mode=None, state=None):
        if mode is None and state is self.state:
            return

        if state is None and mode is self.mode:
            return

        self.clear_display(mode, state)
        self.place_display(mode, state)

        if mode is not None:
            self.mode = mode

        if state is not None:
            self.state = state

    def reset_notification(self):
        self.anchor['text'] = ''

    def set_notify_warning(self):
        self.anchor['text'] = '⚠'

    class Decorators:
        @classmethod
        def reset_progress(cls, f):
            def wrapper(self, *args, **kwargs):
                self.set_progress(0)
                f(self, *args, **kwargs)

            return wrapper

        @classmethod
        def show_progress(cls, f):
            def wrapper(self, *args, **kwargs):
                self.set_progress(0)
                f(self, *args, **kwargs)
                self.set_progress(100)

            return wrapper

    @Decorators.reset_progress
    def on_click_open(self):
        self.layout_display(SIModes.OPEN, None)

    @Decorators.reset_progress
    def on_click_close(self):
        self.layout_display(SIModes.NONE, SIStates.NONE)

        self.squash.close()
        self.squash = None

    @Decorators.reset_progress
    def on_click_insert(self):
        self.layout_display(None, SIStates.INSERT)

    @Decorators.reset_progress
    def on_click_select(self):
        self.layout_display(None, SIStates.SELECT)

    @Decorators.reset_progress
    def on_click_update(self):
        self.layout_display(None, SIStates.UPDATE)

    def on_carriage_return(self, event=None):
        self.reset_notification()

        text = self.e_text.get().strip()

        if self.mode is SIModes.OPEN:
            try:
                self.open_database_file(text)
            except FileNotFoundError:
                self.set_notify_warning()
            else:
                self.layout_display(SIModes.ACTIVE, SIStates.NONE)
            return

        if self.state is SIStates.SELECT:
            self.select_database_entry(text)
            return

        if self.state is SIStates.UPDATE:
            self.clear_figure()

            try:
                self.update_database_entry(text)
            except FileNotFoundError:
                self.set_notify_warning()
            return

    def on_click_browse(self):
        path = filedialog.askopenfilename(initialdir=os.getcwd())

        self.e_text.delete(0, tk.END)
        self.e_text.insert(0, path)

        self.on_carriage_return()

    def on_click_register(self):
        serial = self.e_serial.get().strip()
        location = self.e_location.get().strip()
        comment = self.e_comment.get().strip()

        self.insert_database_entry([serial, location, comment])

    def on_click_edit(self):
        qrcode = self.e_qrcode.get().strip()
        location = self.e_location.get().strip()
        comment = self.e_comment.get().strip()
        status = self.s_calib.get()[-1] + self.s_token.get()[-1]

        self.modify_database_entry([qrcode, location, comment, status])

        query = self.query

        self.layout_display(self.mode, self.state)
        self.select_database_entry(query)

    def on_edit_entry(self, event):
        self.index = int(event.widget.selection()[0].split('_')[0])

        entry = self.squash.label(self.results[self.index])

        self.e_serial.configure(state='normal')
        self.e_serial.delete(0, tk.END)
        self.e_serial.insert(0, entry['serial'])
        self.e_serial.configure(state='disabled')

        self.e_qrcode.delete(0, tk.END)
        self.e_qrcode.insert(0, entry['id'])

        location = entry['location'].split(', ')[-1].split('[')[0]
        self.e_location.set('  {}'.format(location.strip()))

        self.s_calib.set(' G/P: {}'.format(entry['status'][0]))
        self.s_token.set(' TP: {}'.format(entry['status'][1]))

        self.l_serial.grid(column=0, row=6, pady=2, sticky='e')
        self.e_serial.grid(column=1, row=6, pady=2, sticky='we')
        self.l_qrcode.grid(column=0, row=7, pady=2, sticky='e')
        self.e_qrcode.grid(column=1, row=7, pady=2, sticky='we')
        self.l_location.grid(column=0, row=8, pady=2, sticky='e')
        self.e_location.grid(column=1, row=8, pady=2, sticky='we')
        self.l_comment.grid(column=0, row=9, pady=2, sticky='e')
        self.e_comment.grid(column=1, row=9, pady=2, sticky='we')
        self.l_status.grid(column=0, row=10, rowspan=2, sticky='e')
        self.s_calib.grid(column=1, row=10, sticky='w')
        self.s_token.grid(column=1, row=11, sticky='w')

        self.b_record['text'] = 'edit'
        self.b_record['command'] = self.on_click_edit
        self.b_record.grid(column=0, row=12, columnspan=2, rowspan=1, pady=4)

    def set_progress(self, i):
        self.p_bar['value'] = i
        self.p_bar.update()

    @Decorators.show_progress
    def open_database_file(self, text):
        if os.path.isfile(text) is False:
            raise FileNotFoundError

        self.squash = SquashHelper(text)

    @Decorators.show_progress
    def create_database_file(self, text):
        if os.path.isfile(text) is True:
            raise FileExistsError

        self.squash = SquashHelper(text)
        self.squash.create()

    @Decorators.show_progress
    def insert_database_entry(self, data):
        serial, location, comment = data

        query = 'WHERE serial = {}'.format(repr(serial))
        if len(self.squash.select(query)) > 0:
            return

        pedes = np.zeros((64, 2))
        gains = np.zeros((64, 2))
        files = [''] * 4

        timestamp = datetime.now().strftime('%y%m%d-%H:%M:%S')

        entry = {
            'serial': serial,
            'id': '',
            'pedes': np.array_repr(pedes),
            'gains': np.array_repr(gains),
            'location': '{} [{}]'.format(location, timestamp),
            'history': 'INSERT: [{}]'.format(timestamp),
            'comment': comment,
            'status': '??',
            'files': ', '.join(files),
        }

        self.squash.insert(entry.keys(), entry.values())

    @Decorators.show_progress
    def update_database_entry(self, text):
        if os.path.isfile(text) is False:
            raise FileNotFoundError

        entry, _, _, y, pars, _ = self.squash.parse(
            text, callback=self.set_progress
        )

        serial = entry['serial']
        group = entry['offset'] // 16

        condition = 'WHERE serial = {}'.format(repr(serial))

        data = self.squash.label(self.squash.select(condition)[0])

        files = data['files'].split(', ')
        files[group] = entry['files'].split(', ')[group]

        i_min = group * 16
        i_max = i_min + 16

        pedes = eval(data['pedes'].replace('\\n', ''))
        gains = eval(data['gains'].replace('\\n', ''))
        pedes[i_min:i_max] = eval(entry['pedes'])[i_min:i_max]
        gains[i_min:i_max] = eval(entry['gains'])[i_min:i_max]

        entry['files'] = ', '.join(files)
        entry['pedes'] = np.array_repr(pedes)
        entry['gains'] = np.array_repr(gains)

        entry['location'] = data['location']
        entry['history'] = ', '.join([data['history'], entry['history']])
        entry['comment'] = data['comment']
        entry['status'] = data['status']

        self.squash.update(*zip(*entry.items()), condition)

        # draw pulse maximum vs steps
        pulse_max_vs_step_disp_opts = {
            'yrange': (0, 18000, 4000),
            'interval': 4,
            'labels': ('pulse #', 'pulse maximum'),
            'canvas': (3.6, 3.0),
            'margins': (1.5, 0.2, 0.2, 1.0),
            'fmt_str': [
                'serial {}',
                'channel {}',
                '[{:.0f}, {:.0f}]',
            ],
            'fmt_data': [
                [(serial,)] * y.shape[0],
                list(zip(range(i_min, i_max))),
                pars.tolist(),
            ],
            'output': None,
        }

        self.fig = draw_graph(y, None, **pulse_max_vs_step_disp_opts)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.f_box)
        self.canvas.get_tk_widget().pack(expand=True)
        self.canvas.draw()

    def _one(self, node, key, tags, values, label=None):
        text = key if label is None else label
        self.t_info.insert(
            node,
            tk.END,
            '_'.join([node, key]),
            tags=[tags],
            text=text,
            values=[values],
        )

    def _all(self, node, key, tags, values, label=None):
        self._one(node, key, tags[0], values[0], label=label)

        _node = '_'.join([node, key])
        for i, v in enumerate(values[1:]):
            _key = '_'.join([_node, str(i)])
            _value = ' > ' + v

            self._one(_node, _key, tags[1], _value, label='')

    def _insert(self, node, key, tags, values, label=None):
        if not isinstance(values, list):
            return self._one(node, key, tags, values, label=label)

        _tags = [tags, tags] if not isinstance(tags, list) else tags

        return self._all(node, key, _tags, values, label=label)

    @Decorators.show_progress
    def select_database_entry(self, text):
        self.t_info.delete(*self.t_info.get_children())

        self.results = self.squash.select(text)
        self.query = text
        self.index = None

        for i, data in enumerate(self.results):
            e_id = str(i)

            entry = self.squash.label(data)

            locat = entry['location'].split(', ')
            histo = entry['history'].split(', ')
            statu = 'G/P: {} | TP: {}'.format(*entry['status'])
            files = [x if x else '-' for x in entry['files'].split(', ')]

            self.t_info.insert('', tk.END, e_id, text=entry['serial'])

            self._insert(e_id, 'board ID', 'info', entry['id'])
            self._insert(e_id, 'location', 'info', locat[::-1])
            self._insert(e_id, 'history', 'info', histo[::-1])
            self._insert(e_id, 'comment', 'info', entry['comment'])
            self._insert(e_id, 'status', 'info', statu)
            self._insert(e_id, 'files', 'info', ['<expand>'] + files)
            self._insert(e_id, 'edit', 'edit', '', label='<edit>')

            self.set_progress(i * 100 / len(self.results))

    @Decorators.show_progress
    def modify_database_entry(self, data):
        qrcode, location, comment, status = data

        timestamp = datetime.now().strftime('%y%m%d-%H:%M:%S')

        entry = self.squash.label(self.results[self.index])

        def _update_string(text, fmt_str, fmt_data, sep):
            if not fmt_data[0]:
                return text

            parts = [x for x in text.split(sep) if x]
            parts.append(fmt_str.format(*fmt_data))

            return sep.join(parts)

        if entry['location'].split(', ')[-1].startswith(location):
            location = ''

        entry['id'] = qrcode

        entry['location'] = _update_string(
            entry['location'], '{} [{}]', [location, timestamp], ', '
        )
        entry['comment'] = _update_string(
            entry['comment'], '{}', [comment], '; '
        )
        entry['history'] = _update_string(
            entry['history'], 'EDIT [{}]', [timestamp], ', '
        )

        entry['status'] = status

        condition = 'WHERE serial = {}'.format(repr(entry['serial']))

        self.squash.update(*zip(*entry.items()), condition)


if __name__ == '__main__':
    root = tk.Tk()
    interface = SquashInterface(root)
    root.mainloop()
