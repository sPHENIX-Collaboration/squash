# pylint: disable=missing-docstring,invalid-name

import os
from enum import Enum

import tkinter as tk
from tkinter import filedialog

from display import draw_graph
from helper import SquashHelper
from utils import slice_from_string


class SIModes(Enum):
    WAITING = 0
    ACTIVE = 1


class SIStates(Enum):
    NONE = 0
    OPEN = 1
    INSERT = 2
    SELECT = 3


class SquashInterface:
    def __init__(self, master):
        self.master = master
        self.squash = None

        self.mode = SIModes.WAITING
        self.state = SIStates.NONE

        self.results = None
        self.selection = None

        self.init_frames()

        self.create_widgets()
        self.layout_display()

    def init_frames(self):
        self.frame = tk.Frame(self.master, width=400, height=600)
        self.frame.pack()

    def create_widgets(self):
        self.b_open = tk.Button(self.frame, text='open')
        self.b_open['command'] = self.on_click_open

        self.b_browse = tk.Button(self.frame, text='browse')
        self.b_browse['command'] = self.on_click_browse

        self.b_insert = tk.Button(self.frame, text='insert')
        self.b_insert['command'] = self.on_click_insert

        self.b_select = tk.Button(self.frame, text='select')
        self.b_select['command'] = self.on_click_select

        self.b_close = tk.Button(self.frame, text='close')
        self.b_close['command'] = self.on_click_close

        self.e_text = tk.Entry(self.frame)
        self.e_text.bind('<Key-Return>', self.on_carriage_return)

        self.l_info = tk.Listbox(self.frame, borderwidth=0)
        self.l_info.bind('<<ListboxSelect>>', self.on_select_entry)

        self.b_draw = tk.Button(self.frame, text='draw')
        self.b_draw['command'] = self.on_click_draw

        self.e_chan = tk.Entry(self.frame)
        self.l_chan = tk.Label(self.frame, text='channel')
        self.e_pulse = tk.Entry(self.frame)
        self.l_pulse = tk.Label(self.frame, text='pulse')

        self.b_edit = tk.Button(self.frame, text='append')
        self.b_edit['command'] = self.on_click_edit

        self.e_edit = tk.Entry(self.frame)

    def clear_widgets(self):
        self.b_open.place_forget()
        self.b_browse.place_forget()
        self.b_insert.place_forget()
        self.b_select.place_forget()
        self.b_close.place_forget()

        if self.state is SIStates.NONE:
            self.e_text.place_forget()
            self.l_info.place_forget()

        if self.state is not SIStates.SELECT:
            self.b_draw.place_forget()
            self.e_chan.place_forget()
            self.l_chan.place_forget()
            self.e_pulse.place_forget()
            self.l_pulse.place_forget()
            self.b_edit.place_forget()
            self.e_edit.place_forget()

        self.e_text.delete(0, tk.END)
        self.l_info.delete(0, tk.END)
        self.e_chan.delete(0, tk.END)
        self.e_pulse.delete(0, tk.END)

    def layout_display(self, mode=None, state=None):
        if mode is not None:
            self.mode = mode

        if state is not None:
            self.state = state

        self.clear_widgets()

        if self.state is not SIStates.NONE:
            self.e_text.place(x=30, y=40, width=280)
            self.l_info.place(x=30, y=75, width=280, height=450)

        if self.state in (SIStates.OPEN, SIStates.INSERT):
            self.b_browse.place(x=320, y=40, width=75)

        if self.state is SIStates.SELECT:
            self.b_draw.place(x=30, y=510, width=80)
            self.e_chan.place(x=130, y=510, width=80)
            self.l_chan.place(x=130, y=540, width=80)
            self.e_pulse.place(x=230, y=510, width=80)
            self.l_pulse.place(x=230, y=540, width=80)
            self.b_edit.place(x=30, y=480, width=80)
            self.e_edit.place(x=130, y=480, width=180)

        if self.mode is SIModes.WAITING:
            self.b_open.place(x=130, y=10, width=80)
            return

        if self.mode is SIModes.ACTIVE:
            self.b_insert.place(x=30, y=10, width=80)
            self.b_select.place(x=130, y=10, width=80)
            self.b_close.place(x=230, y=10, width=80)
            return

    def switch_layout(self, mode):
        self.layout_display(mode, SIStates.NONE)

    def on_click_open(self):
        self.layout_display(SIModes.WAITING, SIStates.OPEN)

    def on_click_browse(self):
        path = filedialog.askopenfilename(initialdir=os.getcwd())

        self.e_text.delete(0, tk.END)
        self.e_text.insert(0, path)
        self.on_carriage_return()

    def on_click_insert(self):
        self.layout_display(SIModes.ACTIVE, SIStates.INSERT)

    def on_click_select(self):
        self.layout_display(SIModes.ACTIVE, SIStates.SELECT)

    def on_click_close(self):
        self.close_database_file()

        self.squash = None
        self.selection = None

        self.switch_layout(SIModes.WAITING)

    def on_click_draw(self):
        if self.results is None or self.selection is None:
            return

        mean, sigma, y, pars, _ = self.squash.object.parser(
            self.results[self.selection][0], output='signal'
        )

        c_slice = slice_from_string(self.e_chan.get())
        p_slice = slice_from_string(self.e_pulse.get())

        def is_null_slice(s):
            return not any([s.start, s.stop, s.step])

        c_null = is_null_slice(c_slice)
        p_null = is_null_slice(p_slice)

        disp_opts = {}

        if c_null is False and p_null is False:
            return

        if c_null is True and p_null is True:
            labels = list(zip(range(y.shape[0])))

            disp_opts['yrange'] = (0, 18000, 4000)
            disp_opts['interval'] = 5
            disp_opts['labels'] = ('pulse #', 'pulse maximum')
            disp_opts['fmt_str'] = ['channel {}', '[{:.0f}, {:.0f}]']
            disp_opts['fmt_data'] = [labels, pars.tolist()]

            draw_graph(y, None, **disp_opts)
        else:
            disp_opts['yrange'] = (0, 18000, 4000)
            disp_opts['interval'] = 5
            disp_opts['labels'] = ('sample #', 'ADC value')

            if c_null is True:
                disp_opts['fmt_str'] = ['channel {}']
                disp_opts['fmt_data'] = [list(zip(range(mean.shape[1])))]
            else:
                disp_opts['fmt_str'] = ['pulse {}']
                disp_opts['fmt_data'] = [list(zip(range(mean.shape[0])))]

            selection = p_slice, c_slice

            draw_graph(mean[selection], sigma[selection], **disp_opts)

    def on_click_edit(self):
        text = self.e_edit.get()

        self.append_database_entry(text)

    def on_select_entry(self, event):
        selection = event.widget.curselection()

        if selection is not None:
            self.selection = selection[0]

    def on_carriage_return(self, event=None):
        text = self.e_text.get()

        if self.state is SIStates.OPEN:
            try:
                self.open_database_file(text)
            except FileNotFoundError:
                pass
            else:
                self.switch_layout(SIModes.ACTIVE)
            return

        if self.state is SIStates.INSERT:
            self.insert_database_entry(text)
            return

        if self.state is SIStates.SELECT:
            self.select_database_entries(text)
            return

    def open_database_file(self, path):
        if os.path.isfile(path) is False:
            raise FileNotFoundError

        self.squash = SquashHelper(path)

    def insert_database_entry(self, path):
        if os.path.isfile(path) is False:
            raise FileNotFoundError

        self.squash.insert(path)

    def append_database_entry(self, text):
        if self.selection is None:
            return

        label = self.results[self.selection][0]
        condition = 'WHERE label = \'{}\''.format(label)

        self.squash.append(['info'], [text], condition)

    def select_database_entries(self, text):
        query = '*' if not text else text
        self.results = self.squash.select(query)

        for entry in self.results:
            self.l_info.insert(tk.END, str(entry))

    def close_database_file(self):
        self.squash.close()


if __name__ == '__main__':
    root = tk.Tk()
    interface = SquashInterface(root)
    root.mainloop()
