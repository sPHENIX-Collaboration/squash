# pylint: disable=missing-docstring,invalid-name

from datetime import datetime
from enum import Enum
import os
import re

from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
from numpy import array
import tkinter as tk
import tkinter.font
from tkinter import filedialog, ttk

from display import draw_graph
from helper import SquashHelper
from utils import slice_from_string


ADC_DB_PATH = ''
XMIT_DB_PATH = ''


class SIModes(Enum):
    NONE = 0
    OPEN = 1
    LOGIN = 2
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
        self.version = None

        self.mode = SIModes.NONE
        self.state = SIStates.NONE

        self.scale = 1.0
        self.fontsizes = {}

        self.user = None
        self.dir = None
        self.results = None
        self.query = None
        self.index = None

        self.fig = None
        self.canvas = None

        self.init_root()

        self.init_frames()
        self.init_widgets()

        self.init_display()

    def init_root(self):
        self.master.geometry('800x600')
        self.master.title('pumpkin.py')
        self.master.iconphoto(False, ImageTk.PhotoImage(Image.open('icon.png')))

        for name in tkinter.font.names(self.master):
            font = tkinter.font.Font(root=self.master, name=name, exists=True)
            self.fontsizes[str(font)] = font['size']

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

        self.h_bar = ttk.Separator(self.frame, orient='horizontal')
        self.f_view = ttk.Frame(self.frame, relief='groove')

        self.f_view.columnconfigure(0, weight=1)
        self.f_view.rowconfigure(0, weight=1)

        self.c_view = tk.Canvas(self.f_view, highlightthickness=0)

        self.c_view.columnconfigure(0, weight=1)
        self.c_view.rowconfigure(0, weight=1)

        self.f_box = ttk.Frame(self.c_view)

        self.f_box.columnconfigure(3, weight=1)
        self.f_box.columnconfigure(5, weight=1)
        self.f_box.rowconfigure(6, weight=1)
        self.f_box.rowconfigure(16, weight=1)

        self.p_bar = ttk.Progressbar(
            self.frame,
            orient='horizontal',
            mode='determinate',
        )
        self.l_bar = ttk.Label(self.frame)

        self.s_zoom = ttk.Scale(self.frame, orient='horizontal', from_=0.5, to=2.0)
        self.s_zoom['command'] = self.scale_root
        self.s_zoom.set(1.0)

    def init_widgets(self):
        self.b_action = ttk.Button(self.frame, text='action', width=6)

        self.e_text = ttk.Entry(self.frame)
        self.e_text.bind('<Key-Return>', self.on_carriage_return)

        self.b_power = ttk.Button(self.frame, text='power', width=6)

        self.b_adc = ttk.Button(self.frame, text='adc', width=6)
        self.b_adc['command'] = self.on_click_adc
        self.b_xmit = ttk.Button(self.frame, text='xmit', width=6)
        self.b_xmit['command'] = self.on_click_xmit

        self.b_insert = ttk.Button(self.frame, text='insert', width=6)
        self.b_insert['command'] = self.on_click_insert
        self.b_update = ttk.Button(self.frame, text='update', width=6)
        self.b_update['command'] = self.on_click_update
        self.b_select = ttk.Button(self.frame, text='select', width=6)
        self.b_select['command'] = self.on_click_select

        self.l_user = ttk.Label(self.f_box, text='user:', anchor='e', width=6)
        self.e_user = ttk.Entry(self.f_box, width=12)
        self.e_user.bind('<Key-Return>', self.on_click_continue)
        self.b_cont = ttk.Button(self.f_box, text='continue', width=8)
        self.b_cont['command'] = self.on_click_continue

        self.l_serial = ttk.Label(self.f_box, text='serial #:', anchor='e', width=8)
        self.e_serial = ttk.Entry(self.f_box, width=12)
        self.l_qrcode = ttk.Label(self.f_box, text='QR code:', anchor='e', width=8)
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
        self.e_location.bind('<<ComboboxSelected>>', self.on_select_location)

        self.l_install = ttk.Label(self.f_box, text='install:', anchor='e', width=8)
        self.e_install = ttk.Entry(self.f_box, width=12)

        self.l_comment = ttk.Label(self.f_box, text='comment:', anchor='e', width=8)
        self.e_comment = ttk.Entry(self.f_box, width=12)

        self.l_status = ttk.Label(self.f_box, text='status:', anchor='e', width=8)
        self.s_calib = ttk.Spinbox(self.f_box, state=['readonly'], width=12)
        self.s_calib['values'] = (' G/P: ?', ' G/P: P', ' G/P: F')
        self.s_token = ttk.Spinbox(self.f_box, state=['readonly'], width=12)
        self.s_token['values'] = (' TP: ?', ' TP: P', ' TP: F')

        self.b_record = ttk.Button(self.f_box, text='record', width=8)

        self.l_token = ttk.Label(self.f_box, text='tp data:', anchor='e', width=8)
        self.e_token = ttk.Entry(self.f_box, width=12)
        self.b_token = ttk.Button(self.f_box, text='...', width=1)
        self.b_token['command'] = self.on_click_token

        self.t_info = ttk.Treeview(self.f_box, selectmode='browse')
        self.t_info.bind('<<TreeviewSelect>>', self.on_select_entry)
        self.t_info['columns'] = ['info']
        self.t_info.heading('info', text='...')
        self.t_info.tag_configure('edit', foreground='red')
        self.t_info.tag_configure('pass', background='#abe9b3')
        self.t_info.tag_configure('warn', background='#f8bd96')
        self.t_info.tag_bind('edit', '<ButtonRelease-1>', self.on_edit_entry)

        self.f_draw = ttk.Labelframe(self.frame)

        self.f_draw.columnconfigure(2, weight=1)
        self.f_draw.rowconfigure(0, weight=1)
        self.f_draw.rowconfigure(3, weight=1)

        self.n_draw = ttk.Notebook(self.f_draw)

        self.f_summary = ttk.Frame(self.n_draw)
        self.f_channel = ttk.Frame(self.n_draw)

        self.f_summary.columnconfigure(0, minsize=80)
        self.f_summary.columnconfigure(1, minsize=120)
        self.f_channel.columnconfigure(0, minsize=80)
        self.f_channel.columnconfigure(1, minsize=120)

        self.n_draw.add(self.f_summary, text='summary')
        self.n_draw.add(self.f_channel, text=' pulse ')

        self.b_draw = ttk.Button(self.f_draw, text='draw', width=6)
        self.b_draw['command'] = self.on_click_draw
        self.b_save = ttk.Button(self.f_draw, text='save', width=6)
        self.b_save['command'] = self.on_click_save
        self.b_save['state'] = 'disabled'

        self.b_back = ttk.Button(self.f_box, text='back', width=6)
        self.b_back['command'] = self.on_click_back

        self.l_summary = ttk.Label(self.f_summary, text='channel', anchor='e')
        self.e_summary = ttk.Entry(self.f_summary, width=9)
        self.l_channel = ttk.Label(self.f_channel, text='channel', anchor='e')
        self.e_channel = ttk.Entry(self.f_channel, width=9)
        self.l_pulse = ttk.Label(self.f_channel, text='pulse', anchor='e')
        self.e_pulse = ttk.Entry(self.f_channel, width=9)

        self.sb_x = ttk.Scrollbar(self.f_view, orient='horizontal')
        self.sb_x.config(command=self.c_view.xview)
        self.sb_y = ttk.Scrollbar(self.f_view, orient='vertical')
        self.sb_y.config(command=self.c_view.yview)
        self.sb_r = ttk.Label(self.f_view, text='⟳')
        self.sb_r.bind('<ButtonRelease-1>', self.refresh_figure)

        self.c_view.config(xscrollcommand=self.sb_x.set)
        self.c_view.config(yscrollcommand=self.sb_y.set)

    def refresh_display(self):
        self.main.grid_forget()

        self.init_display()

        self.layout_display(self.mode, self.state)

    def init_display(self):
        self.main.grid(column=0, row=0, sticky='nswe')
        self.frame.grid(column=0, row=0, padx=8, pady=4, sticky='nswe')

        self.b_power.grid(column=0, row=0, padx=8, pady=2, sticky='we')
        self.h_bar.grid(column=0, row=1, columnspan=7, rowspan=1, sticky='we')
        self.f_view.grid(
            column=1,
            row=2,
            columnspan=6,
            rowspan=5,
            padx=4,
            pady=4,
            sticky='nswe',
        )

        self.c_view.grid(column=0, row=0, padx=2, pady=2, sticky='nswe')
        self.w_view = self.c_view.create_window(
            0, 0, window=self.f_box, anchor='nw'
        )

        def _fill_canvas(event):
            if event.width > self.f_box.winfo_width():
                self.c_view.itemconfig(self.w_view, width=event.width)

            if event.height > self.f_box.winfo_height():
                self.c_view.itemconfig(self.w_view, height=event.height)

        self.c_view.bind('<Configure>', _fill_canvas)

        self.p_bar.grid(column=1, row=8, columnspan=6, padx=8, sticky='we')
        self.l_bar.grid(column=1, row=9, columnspan=6, padx=4, sticky='we')

        self.s_zoom.grid(column=0, row=8, rowspan=2, padx=8, sticky='we')

        self.sb_x.grid(column=0, row=1, padx=2, pady=2, sticky='nswe')
        self.sb_y.grid(column=1, row=0, padx=2, pady=2, sticky='nswe')
        self.sb_r.grid(column=1, row=1, padx=2, pady=2, sticky='nswe')

        self.layout_display(self.mode, self.state)

    def scale_root(self, value):
        scale = float(value)

        if abs((rel := scale / self.scale) - 1.0) < 0.1:
            return

        self.master.tk.call('tk', 'scaling', rel)

        for name in tkinter.font.names(self.master):
            font = tkinter.font.Font(root=self.master, name=name, exists=True)
            font['size'] = round(self.fontsizes[str(font)] * scale)

        self.refresh_display()

        self.scale = scale

    def reset_view(self):
        self.c_view.xview_moveto(0)
        self.c_view.yview_moveto(0)

    def place_canvas(self):
        self.canvas.get_tk_widget().grid(column=4, row=7, sticky='nswe')

        if self.state is SIStates.SELECT:
            self.b_save['state'] = 'normal'
            self.b_back.grid(column=4, row=8, padx=4, pady=4)

    def clear_canvas(self):
        self.canvas.get_tk_widget().grid_forget()

        if self.state is SIStates.SELECT:
            self.b_save['state'] = 'disabled'
            self.b_back.grid_forget()

    def update_bounds(self):
        self.master.update()

        if (width := self.f_box.winfo_reqwidth()) > self.f_view.winfo_width() - 4:
            self.c_view.itemconfig(self.w_view, width=width)

        if (height := self.f_box.winfo_reqheight()) > self.f_view.winfo_height() - 4:
            self.c_view.itemconfig(self.w_view, height=height)

        self.c_view.config(scrollregion=(0, 0, width, height))

    def refresh_figure(self, event):
        if self.canvas is not None:
            self.clear_canvas()
            self.place_canvas()

        self.update_bounds()

    def place_figure(self):
        if self.canvas is not None:
            self.clear_figure()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.f_box)
        self.canvas.draw()

        self.place_canvas()

        self.update_bounds()

    def clear_figure(self):
        if self.canvas is None:
            return

        self.clear_canvas()

        self.canvas = None

    def clear_action_group(self):
        self.e_text.delete(0, tk.END)
        self.e_text.grid_forget()
        self.b_action.grid_forget()

    def place_install_group(self):
        row = 3 if self.state is SIStates.INSERT else 20

        self.l_install.grid(column=0, row=row, padx=2, pady=1, sticky='we')
        self.e_install.grid(column=1, row=row, padx=2, pady=1, sticky='we')

    def clear_install_group(self):
        self.l_install.grid_forget()
        self.e_install.delete(0, tk.END)
        self.e_install.grid_forget()

    def place_record_group(self):
        self.l_serial.grid(column=0, row=17, padx=2, pady=1, sticky='we')
        self.e_serial.grid(column=1, row=17, padx=2, pady=1, sticky='we')
        self.l_qrcode.grid(column=0, row=18, padx=2, pady=1, sticky='we')
        self.e_qrcode.grid(column=1, row=18, padx=2, pady=1, sticky='we')
        self.l_location.grid(column=0, row=19, padx=2, pady=1, sticky='we')
        self.e_location.grid(column=1, row=19, padx=2, pady=1, sticky='we')
        self.l_comment.grid(column=0, row=21, padx=2, pady=1, sticky='we')
        self.e_comment.grid(column=1, row=21, padx=2, pady=1, sticky='we')
        self.l_token.grid(column=0, row=22, padx=2, pady=1, sticky='we')
        self.e_token.grid(column=1, row=22, padx=2, pady=1, sticky='we')
        self.b_token.grid(column=2, row=22, padx=2, pady=1, sticky='we')
        self.l_status.grid(column=0, row=23, rowspan=2, padx=2, sticky='we')

        if self.version == 'adc':
            self.s_calib.grid(column=1, row=23, padx=2, sticky='w')
        self.s_token.grid(column=1, row=24, padx=2, sticky='w')

        self.b_record['text'] = 'edit'
        self.b_record['command'] = self.on_click_edit
        self.b_record.grid(column=0, row=25, columnspan=2, rowspan=1, pady=4)

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
        self.l_install.grid_forget()
        self.e_install.delete(0, tk.END)
        self.e_install.grid_forget()
        self.l_comment.grid_forget()
        self.e_comment.delete(0, tk.END)
        self.e_comment.grid_forget()
        self.l_token.grid_forget()
        self.e_token.delete(0, tk.END)
        self.e_token.grid_forget()
        self.b_token.grid_forget()
        self.l_status.grid_forget()
        self.s_calib.grid_forget()
        self.s_token.grid_forget()

        self.b_record.grid_forget()

    def place_draw_group(self):
        self.f_draw.grid(column=1, row=7, columnspan=6, rowspan=1, sticky='nswe')
        self.n_draw.grid(column=0, row=0, columnspan=1, rowspan=4, sticky='nswe')
        self.l_summary.grid(column=0, row=0, padx=2, sticky='we')
        self.e_summary.grid(column=1, row=0, padx=2, sticky='we')
        self.l_channel.grid(column=0, row=0, padx=2, sticky='we')
        self.e_channel.grid(column=1, row=0, padx=2, sticky='we')
        self.l_pulse.grid(column=0, row=1, padx=2, sticky='we')
        self.e_pulse.grid(column=1, row=1, padx=2, sticky='we')

        self.b_draw.grid(column=1, row=1, sticky='we')
        self.b_save.grid(column=1, row=2, sticky='we')

    def clear_draw_group(self):
        self.f_draw.grid_forget()
        self.n_draw.grid_forget()
        self.l_summary.grid_forget()
        self.e_summary.delete(0, tk.END)
        self.e_summary.grid_forget()
        self.l_channel.grid_forget()
        self.e_channel.delete(0, tk.END)
        self.e_channel.grid_forget()
        self.l_pulse.grid_forget()
        self.e_pulse.delete(0, tk.END)
        self.e_pulse.grid_forget()

        self.b_draw.grid_forget()
        self.b_save.grid_forget()
        self.b_back.grid_forget()

    def clear_display(self, mode, state):
        self.reset_notification()

        self.clear_figure()

        if mode is SIModes.NONE:
            self.clear_action_group()

            self.b_insert.grid_forget()
            self.b_update.grid_forget()
            self.b_select.grid_forget()

        if mode is SIModes.LOGIN:
            self.clear_action_group()

            self.b_adc.grid_forget()
            self.b_xmit.grid_forget()

        if mode is SIModes.ACTIVE:
            self.l_user.grid_forget()
            self.e_user.delete(0, tk.END)
            self.e_user.grid_forget()

            self.b_cont.grid_forget()

        if state is SIStates.INSERT:
            self.clear_action_group()

        if self.state is SIStates.INSERT:
            self.clear_record_group()

        if self.state is SIStates.UPDATE:
            self.e_text.delete(0, tk.END)

        if self.state is SIStates.SELECT:
            self.e_text.delete(0, tk.END)

            self.t_info.delete(*self.t_info.get_children())
            self.t_info.grid_forget()

            self.clear_record_group()
            self.clear_draw_group()

            self.results = None
            self.query = None
            self.index = None

    def place_display(self, mode=None, state=None):
        self.reset_view()

        if mode is SIModes.NONE:
            self.b_power['text'] = 'open'
            self.b_power['command'] = self.on_click_open
            self.b_power.bind('<Key-Return>', self.on_click_open)

            self.b_power.focus_set()

        if mode is SIModes.OPEN:
            self.e_text.grid(
                column=1, row=0, columnspan=5, rowspan=1, padx=8, sticky='we'
            )

            self.b_action['text'] = 'browse'
            self.b_action['command'] = self.on_click_browse
            self.b_action.grid(column=6, row=0, padx=4)

            self.b_adc.grid(column=0, row=2, padx=8, sticky='we')
            self.b_xmit.grid(column=0, row=3, padx=8, sticky='we')

            self.e_text.focus_set()

        if mode is SIModes.LOGIN:
            self.l_user.grid(column=0, row=0, padx=2, pady=1, sticky='we')
            self.e_user.grid(column=1, row=0, padx=2, pady=1, sticky='we')

            self.b_cont.grid(column=0, row=1, columnspan=2, rowspan=1, pady=4)

            self.e_user.focus_set()

        if mode is SIModes.ACTIVE:
            self.b_power['text'] = 'close'
            self.b_power['command'] = self.on_click_close
            self.b_power.unbind('<Key-Return>')

            self.b_insert.grid(column=0, row=2, padx=8, sticky='we')
            if self.version == 'adc':
                self.b_update.grid(column=0, row=3, padx=8, sticky='we')
            self.b_select.grid(column=0, row=4, padx=8, sticky='we')

        if state is SIStates.INSERT:
            self.l_serial.grid(column=0, row=0, padx=2, pady=1, sticky='we')
            self.e_serial.grid(column=1, row=0, padx=2, pady=1, sticky='we')
            self.l_qrcode.grid(column=0, row=1, padx=2, pady=1, sticky='we')
            self.e_qrcode.grid(column=1, row=1, padx=2, pady=1, sticky='we')
            self.l_location.grid(column=0, row=2, padx=2, pady=1, sticky='we')
            self.e_location.grid(column=1, row=2, padx=2, pady=1, sticky='we')
            self.l_comment.grid(column=0, row=4, padx=2,pady=1, sticky='we')
            self.e_comment.grid(column=1, row=4, padx=2,pady=1, sticky='we')

            self.b_record['text'] = 'register'
            self.b_record['command'] = self.on_click_register
            self.b_record.grid(column=0, row=5, columnspan=2, rowspan=1, pady=4)

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
                row=6,
                columnspan=6,
                rowspan=11,
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
        self.l_bar['text'] = ''

    def set_notify_info(self, message):
        self.l_bar['text'] = 'ℹ {}'.format(message)

    def set_notify_warning(self, message):
        self.l_bar['text'] = '⚠️ {}'.format(message)

    def set_notify_error(self, message):
        self.l_bar['text'] = '🛑 {}'.format(message)

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

        @classmethod
        def reset_warnings(cls, f):
            def wrapper(self, *args, **kwargs):
                self.reset_notification()
                f(self, *args, **kwargs)

            return wrapper

    @Decorators.reset_warnings
    @Decorators.reset_progress
    def on_click_open(self, event=None):
        self.layout_display(SIModes.OPEN, None)

    @Decorators.reset_warnings
    @Decorators.reset_progress
    def on_click_close(self):
        self.layout_display(SIModes.NONE, SIStates.NONE)

        self.close_database_file()

    @Decorators.reset_warnings
    @Decorators.reset_progress
    def on_click_insert(self):
        self.layout_display(None, SIStates.INSERT)

    @Decorators.reset_warnings
    @Decorators.reset_progress
    def on_click_select(self):
        self.layout_display(None, SIStates.SELECT)

    @Decorators.reset_warnings
    @Decorators.reset_progress
    def on_click_update(self):
        self.layout_display(None, SIStates.UPDATE)

    @Decorators.reset_warnings
    def on_carriage_return(self, event=None):
        self.reset_notification()

        text = self.e_text.get().strip()

        if self.mode is SIModes.OPEN:
            try:
                self.open_database_file(text)
            except FileNotFoundError:
                self.set_notify_warning('file not found')
            else:
                self.layout_display(SIModes.LOGIN, None)
            return

        if self.state is SIStates.SELECT:
            self.clear_figure()

            self.select_database_entry(text)
            return

        if self.state is SIStates.UPDATE:
            self.clear_figure()

            try:
                for t in text.split(', '):
                    self.update_database_entry(t)
            except FileNotFoundError:
                self.set_notify_warning('file not found')
            except IndexError:
                self.set_notify_error('IndexError')
            return

    @Decorators.reset_warnings
    def on_click_browse(self):
        idir = os.getcwd() if self.dir is None else self.dir
        multiple = False if self.mode is SIModes.OPEN else True
        paths = filedialog.askopenfilename(initialdir=idir, multiple=multiple)

        path = ', '.join(paths) if multiple is True else paths

        if not path:
            return

        self.e_text.delete(0, tk.END)
        self.e_text.insert(0, path)

        if multiple is True:
            self.dir = os.path.dirname(paths[0])
        else:
            self.dir = os.path.dirname(path)

        self.on_carriage_return()

    @Decorators.reset_warnings
    def on_click_adc(self):
        self.e_text.delete(0, tk.END)
        self.e_text.insert(0, ADC_DB_PATH)

        self.on_carriage_return()

    @Decorators.reset_warnings
    def on_click_xmit(self):
        self.e_text.delete(0, tk.END)
        self.e_text.insert(0, XMIT_DB_PATH)

        self.on_carriage_return()

    @Decorators.reset_warnings
    def on_click_continue(self, event=None):
        user = self.e_user.get().strip()

        if not user:
            self.set_notify_warning('user must not be empty')
            return

        self.user = user

        self.layout_display(SIModes.ACTIVE, SIStates.NONE)

    @Decorators.reset_warnings
    def on_click_register(self):
        serial = self.e_serial.get().strip()
        qrcode = self.e_qrcode.get().strip()
        location = self.e_location.get().strip()
        install = self.e_install.get().strip()
        comment = self.e_comment.get().strip()

        self.insert_database_entry([
            serial, qrcode, location, install, comment
        ])

        self.set_notify_info('{} registered'.format(serial))

    @Decorators.reset_warnings
    def on_click_edit(self):
        serial = self.e_serial.get().strip()
        qrcode = self.e_qrcode.get().strip()
        location = self.e_location.get().strip()
        install = self.e_install.get().strip()
        comment = self.e_comment.get().strip()
        token = self.e_token.get().strip()
        status = (
            self.s_calib.get()[-1] if self.version == 'adc' else ''
        ) + self.s_token.get()[-1]

        self.modify_database_entry([
            qrcode, location, install, comment, token, status
        ])

        query = self.query

        self.layout_display(self.mode, self.state)
        self.select_database_entry(query)

        self.set_notify_info('{} updated'.format(serial))

    def on_click_token(self):
        idir = os.getcwd() if self.dir is None else self.dir
        path = filedialog.askopenfilename(initialdir=idir)

        relpath = os.path.relpath(path, os.path.dirname(self.squash.path))

        self.e_token.delete(0, tk.END)
        self.e_token.insert(0, relpath)

        self.dir = os.path.dirname(path)

    @Decorators.reset_warnings
    @Decorators.show_progress
    def on_click_draw(self):
        self.clear_figure()

        entry = self.squash.label(self.results[self.index])

        index = self.n_draw.index(self.n_draw.select())

        if index == 0:
            sel = slice_from_string(self.e_summary.get().strip())

            if sel is None:
                self.set_notify_warning('invalid selection')
                return

            files = entry['files'].split(', ')

            g_min = sel.start // 16
            g_max = (sel.stop - 1) // 16 + 1

            if not all(files[g_min:g_max]):
                self.set_notify_warning('data file(s) absent')
                return

            padding = g_min * 16

            _y = np.zeros((padding, 40))
            _p = np.zeros((padding, 2))

            for f in files[g_min:g_max]:
                _, _, _, y, pars, _ = self.squash.parse(
                    os.path.join(os.path.dirname(self.squash.path), f),
                    callback=self.set_progress
                )

                _y = np.vstack((_y, y))
                _p = np.vstack((_p, pars))

            _y = _y[sel,:]
            _p = _p[sel,:]

            pulse_max_vs_step_disp_opts = {
                'yrange': (0, 18000, 4000),
                'interval': 4,
                'labels': ('pulse #', 'pulse maximum'),
                'fmt_str': [
                    '{}',
                    'channel {}',
                    'pedestal: {:.0f}',
                    'gain: {:.0f}',
                ],
                'fmt_data': [
                    [(entry['serial'],)] * _y.shape[0],
                    list(zip(range(sel.start, sel.stop, sel.step))),
                    [(x[0],) for x in _p.tolist()],
                    [(x[1],) for x in _p.tolist()],
                ],
                'output': None,
            }

            self.fig = draw_graph(_y, None, **pulse_max_vs_step_disp_opts)
        elif index == 1:
            csel = slice_from_string(self.e_channel.get().strip())
            psel = slice_from_string(self.e_pulse.get().strip())

            if csel is None or psel is None:
                self.set_notify_warning('invalid selection')
                return

            files = entry['files'].split(', ')

            g_min = csel.start // 16
            g_max = (csel.stop - 1) // 16 + 1

            if not all(files[g_min:g_max]):
                self.set_notify_warning('data file(s) absent')
                return

            padding = g_min * 16

            _m = np.zeros((40, padding, 28))
            _s = np.zeros((40, padding, 28))

            for f in files[g_min:g_max]:
                _, mean, sigma, _, _, _ = self.squash.parse(
                    os.path.join(os.path.dirname(self.squash.path), f),
                    callback=self.set_progress
                )

                _m = np.concatenate((_m, mean), axis=1)
                _s = np.concatenate((_s, sigma), axis=1)

            _m = _m[psel,csel,:]
            _s = _s[psel,csel,:]

            pidx = np.repeat(np.mgrid[[psel]], _m.shape[1], axis=1).flatten()
            cidx = np.repeat(np.mgrid[[csel]], _m.shape[0], axis=0).flatten()

            _m = _m.reshape(-1, _m.shape[-1])
            _s = _s.reshape(-1, _s.shape[-1])

            pulse_vs_sample_disp_opts = {
                'yrange': (0, 18000, 4000),
                'interval': 4,
                'labels': ('sample #', 'ADC value'),
                'info': [0.92, 0.87, 0.08, 'right'],
                'fmt_str': [
                    '{}',
                    'channel {}',
                    'pulse {}',
                ],
                'fmt_data': [
                    [(entry['serial'],)] * _m.shape[0],
                    list(zip(cidx)),
                    list(zip(pidx)),
                ],
                'output': None,
            }

            self.fig = draw_graph(_m, _s, **pulse_vs_sample_disp_opts)

        self.clear_record_group()
        self.t_info.grid_remove()

        self.place_figure()

    @Decorators.reset_warnings
    @Decorators.show_progress
    def on_click_save(self):
        if self.fig is None:
            return

        path = filedialog.asksaveasfilename(
            initialdir=os.getcwd(),
            defaultextension='png',
        )

        if not path:
            return

        self.fig.savefig(path)
        self.set_notify_info('file saved: {}'.format(path))

    @Decorators.reset_warnings
    @Decorators.reset_progress
    def on_click_back(self):
        self.clear_figure()
        self.reset_view()

        self.t_info.grid()

    def on_select_location(self, event):
        if event.widget.get().strip() != 'BNL (sPHENIX)':
            self.clear_install_group()
        else:
            self.place_install_group()

    def on_select_entry(self, event):
        if not (selection := event.widget.selection()):
            return

        self.index = int(selection[0].split('_')[0])

        if self.version != 'adc':
            return

        entry = self.squash.label(self.results[self.index])

        self.f_draw['text'] = entry['serial']
        self.place_draw_group()

    def on_edit_entry(self, event):
        if not (selection := event.widget.selection()):
            return

        self.index = int(selection[0].split('_')[0])

        entry = self.squash.label(self.results[self.index])

        self.e_serial.configure(state='normal')
        self.e_serial.delete(0, tk.END)
        self.e_serial.insert(0, entry['serial'])
        self.e_serial.configure(state='disabled')

        self.e_qrcode.delete(0, tk.END)
        self.e_qrcode.insert(0, entry['id'])

        p = re.compile('(.*) \[.*\] <.*>')
        location = p.match(entry['location'].split(', ')[-1]).group(1)
        self.e_location.set('  {}'.format(location))

        self.e_install.delete(0, tk.END)
        self.e_install.insert(0, entry['install'].strip())

        self.e_token.delete(0, tk.END)
        self.e_token.insert(0, entry['files'].split(', ')[-1])

        self.s_calib.set(' G/P: {}'.format(entry['status'][0]))
        self.s_token.set(' TP: {}'.format(entry['status'][-1]))

        self.place_record_group()

        self.e_location.event_generate('<<ComboboxSelected>>')

    def set_progress(self, i):
        self.p_bar['value'] = i
        self.p_bar.update()

    def open_database_file(self, text):
        if os.path.isfile(text) is False:
            raise FileNotFoundError

        self.squash = SquashHelper(text)
        self.version = self.squash.version

        self.master.title('[{}] pumpkin.py [{}]'.format(
            self.version, os.path.basename(text))
        )

    def close_database_file(self):
        self.squash.close()
        self.squash = None
        self.version = None

        self.user = None
        self.dir = None

        self.master.title('pumpkin.py')

    @Decorators.show_progress
    def insert_database_entry(self, data):
        serial, qrcode, location, install, comment = data

        query = 'WHERE serial = {}'.format(repr(serial))
        if len(self.squash.select(query)) > 0:
            self.set_notify_warning('{} already exists'.format(serial))
            return

        query = 'WHERE id = {}'.format(repr(qrcode))
        if qrcode != '' and len(self.squash.select(query)) > 0:
            self.set_notify_warning('{} already exists'.format(qrcode))
            return

        if self.version == 'adc':
            files = [''] * 5
        else:
            files = ['']

        timestamp = datetime.now().strftime('%y%m%d-%H:%M:%S')

        if comment:
            comment = '{} [{}] <{}>'.format(comment, timestamp, self.user)

        status = '??' if self.version == 'adc' else '?'

        entry = {
            'serial': serial,
            'id': qrcode,
            'location': '{} [{}] <{}>'.format(location, timestamp, self.user),
            'history': 'INSERT: [{}] <{}>'.format(timestamp, self.user),
            'comment': comment,
            'status': status,
            'files': ', '.join(files),
            'install': install,
        }

        if self.version == 'adc':
            entry['pedes'] = np.array_repr(np.zeros((64, 2)))
            entry['gains'] = np.array_repr(np.zeros((64, 2)))

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
        files[group] = os.path.relpath(
            entry['files'].split(', ')[group],
            os.path.dirname(self.squash.path)
        )

        history = entry['history'] + ' <{}>'.format(self.user)

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
        entry['history'] = ', '.join([data['history'], history])
        entry['status'] = data['status']
        entry['install'] = data['install']

        if entry['comment']:
            comments = [x for x in data['comment'].split('; ') if x]
            comments.extend(entry['comment'].split('; '))
            comments.append(
                '{} parser errors ({}:{}) <{}>'.format(
                    len(entry['comment'].split('; ')), i_min, i_max - 1, self.user
                )
            )
            entry['comment'] = '; '.join(comments)
        else:
            entry['comment'] = data['comment']

        self.squash.update(*zip(*entry.items()), condition)

        # draw pulse maximum vs steps
        pulse_max_vs_step_disp_opts = {
            'yrange': (0, 18000, 4000),
            'interval': 4,
            'labels': ('pulse #', 'pulse maximum'),
            'fmt_str': [
                '{}',
                'channel {}',
                'pedestal: {:.0f}',
                'gain: {:.0f}',
            ],
            'fmt_data': [
                [(serial,)] * y.shape[0],
                list(zip(range(i_min, i_max))),
                [(x[0],) for x in pars.tolist()],
                [(x[1],) for x in pars.tolist()],
            ],
            'output': None,
        }

        self.fig = draw_graph(y, None, **pulse_max_vs_step_disp_opts)

        self.place_figure()

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

        if not text:
            pass
        elif re.match('^E[0-9]{6}$', text):
            text = 'WHERE serial = {}'.format(repr(text))
        elif re.match('^[0-9]{1,3}$', text):
            text = 'WHERE id = {}'.format(repr(text))
        elif not text.upper().startswith('WHERE '):
            text = 'WHERE {}'.format(text)

        self.results = self.squash.select(text)
        self.query = text
        self.index = None

        for i, data in enumerate(self.results):
            e_id = str(i)

            entry = self.squash.label(data)

            s_str = 'G/P: {} | TP: {}' if self.version == 'adc' else 'TP: {}'

            location = entry['location'].split(', ')
            history = entry['history'].split(', ')
            comment = entry['comment'].split('; ')
            status = s_str.format(*entry['status'])
            files = [x if x else '-' for x in entry['files'].split(', ')]

            i_tag = 'info' if entry['id'] else 'warn'
            s_tag = 'pass' if all(x == 'P' for x in entry['status']) else 'warn'

            f_bool = list(map(lambda x: int(x != '-'), files))
            f_info = 'files | {}/4 | {}/1'.format(sum(f_bool[:4]), f_bool[-1])
            f_tag = 'info' if sum(f_bool) == 5 else 'warn'

            e_tag = '' if all(x == '?' for x in entry['status']) else s_tag

            self.t_info.insert('', tk.END, e_id, tags=e_tag, text=entry['serial'])

            self._insert(e_id, 'QR code', i_tag, entry['id'])
            self._insert(e_id, 'location', 'info', location[::-1])
            if location == 'BNL (sPHENIX)':
                self._insert(e_id, 'install', 'info', entry['install'])
            self._insert(e_id, 'history', 'info', history[::-1])
            self._insert(e_id, 'comment', 'info', comment[::-1])
            self._insert(e_id, 'status', s_tag, status)
            self._insert(e_id, f_info, [f_tag, 'info'], ['<expand>'] + files)
            self._insert(e_id, 'edit', 'edit', '', label='<edit>')

            self.set_progress(i * 100 / len(self.results))

    @Decorators.show_progress
    def modify_database_entry(self, data):
        qrcode, location, install, comment, token, status = data

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
            entry['location'],
            '{} [{}] <{}>',
            [location, timestamp, self.user],
            ', '
        )
        entry['comment'] = _update_string(
            entry['comment'],
            '{} [{}] <{}>',
            [comment, timestamp, self.user],
            '; '
        )
        entry['history'] = _update_string(
            entry['history'],
            'EDIT [{}] <{}>',
            [timestamp, self.user],
            ', '
        )

        if token:
            files = entry['files'].split(', ')
            files[-1] = token
            entry['files'] = ', '.join(files)

        entry['status'] = status
        entry['install'] = install

        condition = 'WHERE serial = {}'.format(repr(entry['serial']))

        self.squash.update(*zip(*entry.items()), condition)


if __name__ == '__main__':
    root = tk.Tk()
    interface = SquashInterface(root)
    root.mainloop()
