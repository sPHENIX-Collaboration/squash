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


ADC_DB_PATH = '/gpfs/mnt/gpfs02/sphenix/user/cmcginn/sPHENIXBoards/squash/src/ADC_boards.db'
XMIT_DB_PATH = '/gpfs/mnt/gpfs02/sphenix/user/cmcginn/sPHENIXBoards/squash/src/XMIT_boards.db'


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
    """
    GUI class utilizing tkinter. Creates an interface for accessing and
    editing the sPHENIX Board Database.
    Inherits the master class.
    """
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
        """
        Initializes the application window.
        """
        self.master.geometry('800x600')
        #self.master.title('pumpkin.py')    # Old interface name
        self.master.title('sPHENIX Board Database Editor')
        self.master.iconphoto(False, ImageTk.PhotoImage(Image.open('icon.png')))

        for name in tkinter.font.names(self.master):
            font = tkinter.font.Font(root=self.master, name=name, exists=True)
            self.fontsizes[str(font)] = font['size']

    def init_frames(self):
        """
        Initializes the static application frames.
        """
        # Initializes the UI master object
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self.frame_master = ttk.Frame(self.master)

        self.frame_master.columnconfigure(0, weight=1)
        self.frame_master.rowconfigure(0, weight=1)
        
        # Initializes the main window
        self.frame_mainWindow = ttk.Frame(self.frame_master)

        self.frame_mainWindow.columnconfigure(1, weight=1)
        self.frame_mainWindow.columnconfigure(5, weight=1)
        self.frame_mainWindow.rowconfigure(6, weight=1)

        self.separatorH_main = ttk.Separator(self.frame_mainWindow, orient='horizontal')
        self.frame_primaryUI = ttk.Frame(self.frame_mainWindow, relief='groove')

        self.frame_primaryUI.columnconfigure(0, weight=1)
        self.frame_primaryUI.rowconfigure(0, weight=1)

        self.canvas_primaryUI = tk.Canvas(self.frame_primaryUI, highlightthickness=0)

        self.canvas_primaryUI.columnconfigure(0, weight=1)
        self.canvas_primaryUI.rowconfigure(0, weight=1)

        self.frame_secondaryUI = ttk.Frame(self.canvas_primaryUI)

        self.frame_secondaryUI.columnconfigure(6, weight=1)
        self.frame_secondaryUI.columnconfigure(8, weight=1)
        self.frame_secondaryUI.rowconfigure(7, weight=1)
        self.frame_secondaryUI.rowconfigure(17, weight=1)
        
        # Progress Bar
        self.progressBar_mainView = ttk.Progressbar(
            self.frame_mainWindow,
            orient='horizontal',
            mode='determinate',
        )
        
        # Notification Bar
        self.label_notificationBar = ttk.Label(self.frame_mainWindow)
        
        # Window Scale Slider
        self.scaleSlider_zoom = ttk.Scale(self.frame_mainWindow, orient='horizontal', from_=0.5, to=2.0)
        self.scaleSlider_zoom['command'] = self.scale_root
        self.scaleSlider_zoom.set(1.0)

    def init_widgets(self):
        """
        Initializes the dynamic application frames and elements ("widgets").
        """
        self.button_action = ttk.Button(self.frame_mainWindow, text='Action', width=6)

        self.entry_text = ttk.Entry(self.frame_mainWindow)
        self.entry_text.bind('<Key-Return>', self.on_carriage_return)
        
        # Primary action button
        self.button_power = ttk.Button(self.frame_mainWindow, text='Power', width=6)
        
        # ADC or XMIT database selection
        self.button_adc = ttk.Button(self.frame_mainWindow, text='ADC DB', width=6)
        self.button_adc['command'] = self.on_click_adc
        self.button_xmit = ttk.Button(self.frame_mainWindow, text='XMIT DB', width=6)
        self.button_xmit['command'] = self.on_click_xmit
        
        # Database edit options
        self.button_insert = ttk.Button(self.frame_mainWindow, text='Add New', width=6)
        self.button_insert['command'] = self.on_click_insert
        self.button_update = ttk.Button(self.frame_mainWindow, text='Update', width=6)
        self.button_update['command'] = self.on_click_update
        self.button_select = ttk.Button(self.frame_mainWindow, text='Select', width=6)
        self.button_select['command'] = self.on_click_select
        
        # Database access widgets
        self.label_access_user = ttk.Label(self.frame_secondaryUI, text='User:', anchor='e', width=6)
        self.entry_access_user = ttk.Entry(self.frame_secondaryUI, width=12)
        self.entry_access_user.bind('<Key-Return>', self.on_click_continue)
        self.button_access_continue = ttk.Button(self.frame_secondaryUI, text='Continue', width=8)
        self.button_access_continue['command'] = self.on_click_continue
        
        # Board serial number and QR code entry
        self.label_serialNumber = ttk.Label(self.frame_secondaryUI, text='Serial #:', anchor='e', width=8)
        self.entry_serialNumber = ttk.Entry(self.frame_secondaryUI, width=16)
        self.label_qrCode = ttk.Label(self.frame_secondaryUI, text='QR Code:', anchor='e', width=8)
        self.entry_qrCode = ttk.Entry(self.frame_secondaryUI, width=16)
        
        # Board location selector
        self.label_boardLocation = ttk.Label(self.frame_secondaryUI, text='Location:', anchor='e', width=8)
        self.combobox_boardLocation = ttk.Combobox(self.frame_secondaryUI, state=['readonly'], width=16)
        self.combobox_boardLocation['values'] = (
            '  CU Boulder',
            '  Nevis Labs (Columbia)',
            '  BNL (storage)',
            '  BNL (sPHENIX)',
        )
        self.combobox_boardLocation.set('  CU Boulder')
        self.combobox_boardLocation.bind('<<ComboboxSelected>>', self.on_select_location)
        
        # Board installation information entry
        self.label_installation = ttk.Label(self.frame_secondaryUI, text='Install:', anchor='e', width=8)
        self.label_rack = ttk.Label(self.frame_secondaryUI, text='Rack', anchor='center', width=4)
        self.entry_rack = ttk.Entry(self.frame_secondaryUI, width=4)
        self.label_crate = ttk.Label(self.frame_secondaryUI, text='Crate', anchor='center', width=4)
        self.entry_crate = ttk.Entry(self.frame_secondaryUI, width=4)
        self.label_slot = ttk.Label(self.frame_secondaryUI, text='Slot', anchor='center', width=4)
        self.entry_slot = ttk.Entry(self.frame_secondaryUI, width=4)
        self.label_detector = ttk.Label(self.frame_secondaryUI, text='Detector', anchor='center', width=8)
        self.combobox_detector = ttk.Combobox(self.frame_secondaryUI, state=['readonly'], width=8)
        self.combobox_detector['values'] = ('', 'MBD', 'ECAL', 'HCAL', 'sEPD')
        self.combobox_detector.set('')
        self.label_comment = ttk.Label(self.frame_secondaryUI, text='Comment:', anchor='e', width=8)
        self.entry_comment = ttk.Entry(self.frame_secondaryUI, width=12)
        
        # Board calibration and token pass status selector
        self.label_status = ttk.Label(self.frame_secondaryUI, text='Board Status:', anchor='e', width=8)
        self.spinbox_calibration = ttk.Spinbox(self.frame_secondaryUI, state=['readonly'], width=12)
        self.spinbox_calibration['values'] = (' G/P: ?', ' G/P: P', ' G/P: F')
        self.spinbox_tokenPass = ttk.Spinbox(self.frame_secondaryUI, state=['readonly'], width=12)
        self.spinbox_tokenPass['values'] = (' TP: ?', ' TP: P', ' TP: F')

        self.button_recordStatus = ttk.Button(self.frame_secondaryUI, text='record status', width=8)
        
        # Token pass data entry
        self.label_tokenPass = ttk.Label(self.frame_secondaryUI, text='TP Data:', anchor='e', width=8)
        self.entry_tokenPass = ttk.Entry(self.frame_secondaryUI, width=12)
        self.button_tokenPass = ttk.Button(self.frame_secondaryUI, text='...', width=1)
        self.button_tokenPass['command'] = self.on_click_token
        
        # Board info treeview display
        self.treeview_boardInfo = ttk.Treeview(self.frame_secondaryUI, selectmode='browse')
        self.treeview_boardInfo.bind('<<TreeviewSelect>>', self.on_select_entry)
        self.treeview_boardInfo['columns'] = ['info']
        self.treeview_boardInfo.heading('info', text='...')
        self.treeview_boardInfo.tag_configure('edit', foreground='red')
        self.treeview_boardInfo.tag_configure('pass', background='#abe9b3')
        self.treeview_boardInfo.tag_configure('warn', background='#f8bd96')
        self.treeview_boardInfo.tag_bind('edit', '<ButtonRelease-1>', self.on_edit_entry)

        self.labelframe_draw = ttk.Labelframe(self.frame_mainWindow)

        self.labelframe_draw.columnconfigure(2, weight=1)
        self.labelframe_draw.rowconfigure(0, weight=1)
        self.labelframe_draw.rowconfigure(3, weight=1)

        self.notebook_draw = ttk.Notebook(self.labelframe_draw)

        self.frame_summary = ttk.Frame(self.notebook_draw)
        self.frame_channel = ttk.Frame(self.notebook_draw)

        self.frame_summary.columnconfigure(0, minsize=80)
        self.frame_summary.columnconfigure(1, minsize=120)
        self.frame_channel.columnconfigure(0, minsize=80)
        self.frame_channel.columnconfigure(1, minsize=120)

        self.notebook_draw.add(self.frame_summary, text='summary')
        self.notebook_draw.add(self.frame_channel, text=' pulse ')

        self.button_draw = ttk.Button(self.labelframe_draw, text='Draw', width=6)
        self.button_draw['command'] = self.on_click_draw
        self.button_save = ttk.Button(self.labelframe_draw, text='Save', width=6)
        self.button_save['command'] = self.on_click_save
        self.button_save['state'] = 'disabled'

        self.button_back = ttk.Button(self.frame_secondaryUI, text='Back', width=6)
        self.button_back['command'] = self.on_click_back

        self.label_summary = ttk.Label(self.frame_summary, text='Channel', anchor='e')
        self.entry_summary = ttk.Entry(self.frame_summary, width=9)
        self.label_channel = ttk.Label(self.frame_channel, text='Channel', anchor='e')
        self.entry_channel = ttk.Entry(self.frame_channel, width=9)
        self.label_pulse = ttk.Label(self.frame_channel, text='Pulse', anchor='e')
        self.entry_pulse = ttk.Entry(self.frame_channel, width=9)

        self.scrollbar_x = ttk.Scrollbar(self.frame_primaryUI, orient='horizontal')
        self.scrollbar_x.config(command=self.canvas_primaryUI.xview)
        self.scrollbar_y = ttk.Scrollbar(self.frame_primaryUI, orient='vertical')
        self.scrollbar_y.config(command=self.canvas_primaryUI.yview)
        self.label_scrollbarRefresh = ttk.Label(self.frame_primaryUI, text='⟳')
        self.label_scrollbarRefresh.bind('<ButtonRelease-1>', self.refresh_figure)

        self.canvas_primaryUI.config(xscrollcommand=self.scrollbar_x.set)
        self.canvas_primaryUI.config(yscrollcommand=self.scrollbar_y.set)

    def refresh_display(self):
        """
        Refreshes the window.
        """
        self.frame_master.grid_forget()

        self.init_display()

        self.layout_display(self.mode, self.state)

    def init_display(self):
        """
        
        """
        self.frame_master.grid(column=0, row=0, sticky='nswe')
        self.frame_mainWindow.grid(column=0, row=0, padx=8, pady=4, sticky='nswe')

        self.button_power.grid(column=0, row=0, padx=8, pady=2, sticky='we')
        self.separatorH_main.grid(column=0, row=1, columnspan=7, rowspan=1, sticky='we')
        self.frame_primaryUI.grid(
            column=1,
            row=2,
            columnspan=6,
            rowspan=5,
            padx=4,
            pady=4,
            sticky='nswe',
        )

        self.canvas_primaryUI.grid(column=0, row=0, padx=2, pady=2, sticky='nswe')
        self.w_view = self.canvas_primaryUI.create_window(
            0, 0, window=self.frame_secondaryUI, anchor='nw'
        )

        def _fill_canvas(event):
            if self.fig is not None:
                return

            self.canvas_primaryUI.itemconfig(self.w_view, width=event.width)
            self.canvas_primaryUI.itemconfig(self.w_view, height=event.height)

        self.canvas_primaryUI.bind('<Configure>', _fill_canvas)

        self.progressBar_mainView.grid(column=1, row=8, columnspan=6, padx=8, sticky='we')
        self.label_notificationBar.grid(column=1, row=9, columnspan=6, padx=4, sticky='we')

        self.scaleSlider_zoom.grid(column=0, row=8, rowspan=2, padx=8, sticky='we')

        self.scrollbar_x.grid(column=0, row=1, padx=2, pady=2, sticky='nswe')
        self.scrollbar_y.grid(column=1, row=0, padx=2, pady=2, sticky='nswe')
        self.label_scrollbarRefresh.grid(column=1, row=1, padx=2, pady=2, sticky='nswe')

        self.layout_display(self.mode, self.state)

    def scale_root(self, value):
        """
        Scales the window.
        """
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
        self.canvas_primaryUI.xview_moveto(0)
        self.canvas_primaryUI.yview_moveto(0)

    def place_canvas(self):
        self.canvas.get_tk_widget().grid(column=7, row=8, sticky='nswe')

        if self.state is SIStates.SELECT:
            self.button_save['state'] = 'normal'
            self.button_back.grid(column=7, row=9, padx=4, pady=4)

    def clear_canvas(self):
        self.canvas.get_tk_widget().grid_forget()

        if self.state is SIStates.SELECT:
            self.button_save['state'] = 'disabled'
            self.button_back.grid_forget()

    def update_bounds(self):
        self.master.update()

        if (width := self.frame_secondaryUI.winfo_reqwidth()) > self.frame_primaryUI.winfo_width() - 4:
            self.canvas_primaryUI.itemconfig(self.w_view, width=width)

        if (height := self.frame_secondaryUI.winfo_reqheight()) > self.frame_primaryUI.winfo_height() - 4:
            self.canvas_primaryUI.itemconfig(self.w_view, height=height)

        self.canvas_primaryUI.config(scrollregion=(0, 0, width, height))

    def refresh_figure(self, event):
        if self.canvas is not None:
            self.clear_canvas()
            self.place_canvas()

        self.update_bounds()

    def place_figure(self):
        if self.canvas is not None:
            self.clear_figure()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_secondaryUI)
        self.canvas.draw()

        self.place_canvas()

        self.update_bounds()

    def clear_figure(self):
        if self.canvas is None:
            return

        self.clear_canvas()

        self.canvas = None

    def clear_action_group(self):
        self.entry_text.delete(0, tk.END)
        self.entry_text.grid_forget()
        self.button_action.grid_forget()
    
    
    # Install Group clear and replace functions
    
    
    def place_install_group(self):
        row = 3 if self.state is SIStates.INSERT else 21

        self.label_installation.grid(column=0, row=row, rowspan=2, padx=2, pady=1, sticky='we')
        self.label_rack.grid(column=1, row=row, padx=2, pady=1, sticky='we')
        self.entry_rack.grid(column=1, row=row + 1, padx=2, pady=1, sticky='we')
        self.label_crate.grid(column=2, row=row, padx=2, pady=1, sticky='we')
        self.entry_crate.grid(column=2, row=row + 1, padx=2, pady=1, sticky='we')
        self.label_slot.grid(column=3, row=row, padx=2, pady=1, sticky='we')
        self.entry_slot.grid(column=3, row=row + 1, padx=2, pady=1, sticky='we')
        self.label_detector.grid(column=4, row=row, padx=2, pady=1, sticky='we')
        self.combobox_detector.grid(column=4, row=row + 1, padx=2, pady=1, sticky='we')

    def clear_install_group(self):
        self.label_installation.grid_forget()
        self.label_rack.grid_forget()
        self.entry_rack.delete(0, tk.END)
        self.entry_rack.grid_forget()
        self.label_crate.grid_forget()
        self.entry_crate.delete(0, tk.END)
        self.entry_crate.grid_forget()
        self.label_slot.grid_forget()
        self.entry_slot.delete(0, tk.END)
        self.entry_slot.grid_forget()
        self.label_detector.grid_forget()
        self.combobox_detector.delete(0, tk.END)
        self.combobox_detector.grid_forget()
    
    
    # Record Group clear and replace functions
    
    
    def place_record_group(self):
        self.label_serialNumber.grid(column=0, row=18, padx=2, pady=1, sticky='we')
        self.entry_serialNumber.grid(column=1, row=18, columnspan=3, padx=2, pady=1, sticky='we')
        self.label_qrCode.grid(column=0, row=19, padx=2, pady=1, sticky='we')
        self.entry_qrCode.grid(column=1, row=19, columnspan=3, padx=2, pady=1, sticky='we')
        self.label_boardLocation.grid(column=0, row=20, padx=2, pady=1, sticky='we')
        self.combobox_boardLocation.grid(column=1, row=20, columnspan=3, padx=2, pady=1, sticky='we')
        self.label_comment.grid(column=0, row=23, padx=2, pady=1, sticky='we')
        self.entry_comment.grid(column=1, row=23, columnspan=4, padx=2, pady=1, sticky='we')
        self.label_tokenPass.grid(column=0, row=24, padx=2, pady=1, sticky='we')
        self.entry_tokenPass.grid(column=1, row=24, columnspan=4, padx=2, pady=1, sticky='we')
        self.button_tokenPass.grid(column=5, row=24, padx=2, pady=1, sticky='we')
        self.label_status.grid(column=0, row=25, rowspan=2, padx=2, sticky='we')

        if self.version == 'adc':
            self.spinbox_calibration.grid(column=1, row=25, columnspan=3, padx=2, sticky='w')
        self.spinbox_tokenPass.grid(column=1, row=26, columnspan=3, padx=2, sticky='w')

        self.button_recordStatus['text'] = 'edit'
        self.button_recordStatus['command'] = self.on_click_edit
        self.button_recordStatus.grid(column=0, row=27, columnspan=4, rowspan=1, pady=4)

    def clear_record_group(self):
        self.entry_serialNumber.configure(state='normal')

        self.label_serialNumber.grid_forget()
        self.entry_serialNumber.delete(0, tk.END)
        self.entry_serialNumber.grid_forget()
        self.label_qrCode.grid_forget()
        self.entry_qrCode.delete(0, tk.END)
        self.entry_qrCode.grid_forget()
        self.label_boardLocation.grid_forget()
        self.combobox_boardLocation.delete(0, tk.END)
        self.combobox_boardLocation.grid_forget()
        self.label_installation.grid_forget()
        self.label_rack.grid_forget()
        self.entry_rack.delete(0, tk.END)
        self.entry_rack.grid_forget()
        self.label_crate.grid_forget()
        self.entry_crate.delete(0, tk.END)
        self.entry_crate.grid_forget()
        self.label_slot.grid_forget()
        self.entry_slot.delete(0, tk.END)
        self.entry_slot.grid_forget()
        self.label_detector.grid_forget()
        self.combobox_detector.delete(0, tk.END)
        self.combobox_detector.grid_forget()
        self.label_comment.grid_forget()
        self.entry_comment.delete(0, tk.END)
        self.entry_comment.grid_forget()
        self.label_tokenPass.grid_forget()
        self.entry_tokenPass.delete(0, tk.END)
        self.entry_tokenPass.grid_forget()
        self.button_tokenPass.grid_forget()
        self.label_status.grid_forget()
        self.spinbox_calibration.grid_forget()
        self.spinbox_tokenPass.grid_forget()

        self.button_recordStatus.grid_forget()
    
    
    # Draw Group clear and replace functions
    
    
    def place_draw_group(self):
        self.labelframe_draw.grid(column=1, row=7, columnspan=6, rowspan=1, sticky='nswe')
        self.notebook_draw.grid(column=0, row=0, columnspan=1, rowspan=4, sticky='nswe')
        self.label_summary.grid(column=0, row=0, padx=2, sticky='we')
        self.entry_summary.grid(column=1, row=0, padx=2, sticky='we')
        self.label_channel.grid(column=0, row=0, padx=2, sticky='we')
        self.entry_channel.grid(column=1, row=0, padx=2, sticky='we')
        self.label_pulse.grid(column=0, row=1, padx=2, sticky='we')
        self.entry_pulse.grid(column=1, row=1, padx=2, sticky='we')

        self.button_draw.grid(column=1, row=1, sticky='we')
        self.button_save.grid(column=1, row=2, sticky='we')

    def clear_draw_group(self):
        self.labelframe_draw.grid_forget()
        self.notebook_draw.grid_forget()
        self.label_summary.grid_forget()
        self.entry_summary.delete(0, tk.END)
        self.entry_summary.grid_forget()
        self.label_channel.grid_forget()
        self.entry_channel.delete(0, tk.END)
        self.entry_channel.grid_forget()
        self.label_pulse.grid_forget()
        self.entry_pulse.delete(0, tk.END)
        self.entry_pulse.grid_forget()

        self.button_draw.grid_forget()
        self.button_save.grid_forget()
        self.button_back.grid_forget()
    
    # Display clear and replace functions
    
    def clear_display(self, mode, state):
        self.reset_notification()

        self.clear_figure()

        if mode is SIModes.NONE:
            self.clear_action_group()

            self.button_insert.grid_forget()
            self.button_update.grid_forget()
            self.button_select.grid_forget()

        if mode is SIModes.LOGIN:
            self.clear_action_group()

            self.button_adc.grid_forget()
            self.button_xmit.grid_forget()

        if mode is SIModes.ACTIVE:
            self.label_access_user.grid_forget()
            self.entry_access_user.delete(0, tk.END)
            self.entry_access_user.grid_forget()

            self.button_access_continue.grid_forget()

        if state is SIStates.INSERT:
            self.clear_action_group()

        if self.state is SIStates.INSERT:
            self.clear_record_group()

        if self.state is SIStates.UPDATE:
            self.entry_text.delete(0, tk.END)

        if self.state is SIStates.SELECT:
            self.entry_text.delete(0, tk.END)

            self.treeview_boardInfo.delete(*self.treeview_boardInfo.get_children())
            self.treeview_boardInfo.grid_forget()

            self.clear_record_group()
            self.clear_draw_group()

            self.results = None
            self.query = None
            self.index = None

    def place_display(self, mode=None, state=None):
        self.reset_view()

        if mode is SIModes.NONE:
            self.button_power['text'] = 'Open DB'
            self.button_power['command'] = self.on_click_open
            self.button_power.bind('<Key-Return>', self.on_click_open)

            self.button_power.focus_set()

        if mode is SIModes.OPEN:
            self.entry_text.grid(
                column=1, row=0, columnspan=5, rowspan=1, padx=8, sticky='we'
            )

            self.button_action['text'] = 'Browse'
            self.button_action['command'] = self.on_click_browse
            self.button_action.grid(column=6, row=0, padx=4)

            self.button_adc.grid(column=0, row=2, padx=8, sticky='we')
            self.button_xmit.grid(column=0, row=3, padx=8, sticky='we')

            self.entry_text.focus_set()

        if mode is SIModes.LOGIN:
            self.label_access_user.grid(column=0, row=0, padx=2, pady=1, sticky='we')
            self.entry_access_user.grid(column=1, row=0, padx=2, pady=1, sticky='we')

            self.button_access_continue.grid(column=0, row=1, columnspan=2, rowspan=1, pady=4)

            self.entry_access_user.focus_set()

        if mode is SIModes.ACTIVE:
            self.button_power['text'] = 'Close DB'
            self.button_power['command'] = self.on_click_close
            self.button_power.unbind('<Key-Return>')

            self.button_insert.grid(column=0, row=2, padx=8, sticky='we')
            if self.version == 'adc':
                self.button_update.grid(column=0, row=3, padx=8, sticky='we')
            self.button_select.grid(column=0, row=4, padx=8, sticky='we')

        if state is SIStates.INSERT:
            self.label_serialNumber.grid(column=0, row=0, padx=2, pady=1, sticky='we')
            self.entry_serialNumber.grid(column=1, row=0, columnspan=3, padx=2, pady=1, sticky='we')
            self.label_qrCode.grid(column=0, row=1, padx=2, pady=1, sticky='we')
            self.entry_qrCode.grid(column=1, row=1, columnspan=3, padx=2, pady=1, sticky='we')
            self.label_boardLocation.grid(column=0, row=2, padx=2, pady=1, sticky='we')
            self.combobox_boardLocation.grid(column=1, row=2, columnspan=3, padx=2, pady=1, sticky='we')
            self.label_comment.grid(column=0, row=5, padx=2,pady=1, sticky='we')
            self.entry_comment.grid(column=1, row=5, columnspan=4, padx=2,pady=1, sticky='we')

            self.button_recordStatus['text'] = 'Register'
            self.button_recordStatus['command'] = self.on_click_register
            self.button_recordStatus.grid(column=0, row=6, columnspan=4, rowspan=1, pady=4)

            self.entry_serialNumber.focus_set()

        if state is SIStates.UPDATE:
            self.entry_text.grid(
                column=1, row=0, columnspan=5, rowspan=1, padx=4, sticky='we'
            )

            self.button_action['text'] = 'Browse'
            self.button_action['command'] = self.on_click_browse
            self.button_action.grid(column=6, row=0, padx=4)

            self.entry_text.focus_set()

        if state is SIStates.SELECT:
            self.entry_text.grid(
                column=1, row=0, columnspan=5, rowspan=1, padx=4, sticky='we'
            )

            self.button_action['text'] = 'Filter'
            self.button_action['command'] = self.on_carriage_return
            self.button_action.grid(column=6, row=0, padx=4)

            self.treeview_boardInfo.grid(
                column=0,
                row=7,
                columnspan=9,
                rowspan=12,
                padx=4,
                pady=4,
                sticky='nswe',
            )

            self.entry_text.focus_set()

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
    
    # Notification functions
    
    def reset_notification(self):
        """
        Resets the notification at the bottom of the window to an empty string.
        """
        self.label_notificationBar['text'] = ''

    def set_notify_info(self, message):
        """
        Changes the notification at the bottom of the window to an info icon
        followed by the notification message.
        :param str message: The notification message as a text string.
        """
        self.label_notificationBar['text'] = 'ℹ {}'.format(message)

    def set_notify_warning(self, message):
        """
        Changes the notification at the bottom of the window to a warning icon
        followed by the notification message.
        :param str message: The notification message as a text string.
        """
        self.label_notificationBar['text'] = '⚠️ {}'.format(message)

    def set_notify_error(self, message):
        """
        Changes the notification at the bottom of the window to an error icon
        followed by the notification message.
        :param str message: The notification message as a text string.
        """
        self.label_notificationBar['text'] = '🛑 {}'.format(message)
    
    # Notification and progress bar decorator functions
    
    class Decorators:
        @classmethod
        def reset_progress(cls, f):
            """
            Resets the progress bar at the bottom of the window before running
            the associated function.
            :param function f: The function that is wrapped by the decorator.
            """
            def wrapper(self, *args, **kwargs):
                self.set_progress(0)
                f(self, *args, **kwargs)

            return wrapper

        @classmethod
        def show_progress(cls, f):
            """
            Triggers the display of a progress bar for applicable functions.
            Resets the progress bar to zero before running the function, and
            forces it to 100% once the function is complete.
            :param function f: The function that is wrapped by the decorator.
            """
            def wrapper(self, *args, **kwargs):
                self.set_progress(0)
                f(self, *args, **kwargs)
                self.set_progress(100)

            return wrapper

        @classmethod
        def reset_warnings(cls, f):
            """
            Resets the notification at the bottom of the window before running
            the associated function.
            :param function f: The function that is wrapped by the decorator.
            """
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

        text = self.entry_text.get().strip()

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

        self.entry_text.delete(0, tk.END)
        self.entry_text.insert(0, path)

        if multiple is True:
            self.dir = os.path.dirname(paths[0])
        else:
            self.dir = os.path.dirname(path)

        self.on_carriage_return()

    @Decorators.reset_warnings
    def on_click_adc(self):
        self.entry_text.delete(0, tk.END)
        self.entry_text.insert(0, ADC_DB_PATH)

        self.on_carriage_return()

    @Decorators.reset_warnings
    def on_click_xmit(self):
        self.entry_text.delete(0, tk.END)
        self.entry_text.insert(0, XMIT_DB_PATH)

        self.on_carriage_return()

    @Decorators.reset_warnings
    def on_click_continue(self, event=None):
        user = self.entry_access_user.get().strip()

        if not user:
            self.set_notify_warning('user must not be empty')
            return

        self.user = user

        self.layout_display(SIModes.ACTIVE, SIStates.NONE)

    @Decorators.reset_warnings
    def on_click_register(self):
        serial = self.entry_serialNumber.get().strip()
        qrcode = self.entry_qrCode.get().strip()
        location = self.combobox_boardLocation.get().strip()
        rack = self.entry_rack.get().strip()
        crate = self.entry_crate.get().strip()
        slot = self.entry_slot.get().strip()
        det = self.combobox_detector.get().strip()
        comment = self.entry_comment.get().strip()

        if self.insert_database_entry(
            [serial, qrcode, location, rack, crate, slot, det, comment]
        ) is False:
            return

        self.set_notify_info('{} registered'.format(serial))

    @Decorators.reset_warnings
    def on_click_edit(self):
        serial = self.entry_serialNumber.get().strip()
        qrcode = self.entry_qrCode.get().strip()
        location = self.combobox_boardLocation.get().strip()
        rack = self.entry_rack.get().strip()
        crate = self.entry_crate.get().strip()
        slot = self.entry_slot.get().strip()
        det = self.combobox_detector.get().strip()
        comment = self.entry_comment.get().strip()
        token = self.entry_tokenPass.get().strip()
        status = (
            self.spinbox_calibration.get()[-1] if self.version == 'adc' else ''
        ) + self.spinbox_tokenPass.get()[-1]

        if self.modify_database_entry(
            [qrcode, location, rack, crate, slot, det, comment, token, status]
        ) is False:
            return

        query = self.query

        self.layout_display(self.mode, self.state)
        self.select_database_entry(query)

        self.set_notify_info('{} updated'.format(serial))

    def on_click_token(self):
        idir = os.getcwd() if self.dir is None else self.dir
        path = filedialog.askopenfilename(initialdir=idir)

        relpath = os.path.relpath(path, os.path.dirname(self.squash.path))

        self.entry_tokenPass.delete(0, tk.END)
        self.entry_tokenPass.insert(0, relpath)

        self.dir = os.path.dirname(path)

    @Decorators.reset_warnings
    @Decorators.show_progress
    def on_click_draw(self):
        self.clear_figure()

        entry = self.squash.label(self.results[self.index])

        index = self.notebook_draw.index(self.notebook_draw.select())

        if index == 0:
            sel = slice_from_string(self.entry_summary.get().strip())

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
            csel = slice_from_string(self.entry_channel.get().strip())
            psel = slice_from_string(self.entry_pulse.get().strip())

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
        self.treeview_boardInfo.grid_remove()

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

        self.treeview_boardInfo.grid()

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

        self.labelframe_draw['text'] = entry['serial']
        self.place_draw_group()

    def on_edit_entry(self, event):
        if not (selection := event.widget.selection()):
            return

        self.index = int(selection[0].split('_')[0])

        entry = self.squash.label(self.results[self.index])

        self.entry_serialNumber.configure(state='normal')
        self.entry_serialNumber.delete(0, tk.END)
        self.entry_serialNumber.insert(0, entry['serial'])
        self.entry_serialNumber.configure(state='disabled')

        self.entry_qrCode.delete(0, tk.END)
        self.entry_qrCode.insert(0, entry['id'])

        p = re.compile('(.*) \[.*\] <.*>')
        location = p.match(entry['location'].split(', ')[-1]).group(1)
        self.combobox_boardLocation.set('  {}'.format(location))

        self.entry_rack.delete(0, tk.END)
        self.entry_rack.insert(0, entry['rack'].strip())
        self.entry_crate.delete(0, tk.END)
        self.entry_crate.insert(0, entry['crate'].strip())
        self.entry_slot.delete(0, tk.END)
        self.entry_slot.insert(0, entry['slot'].strip())
        self.combobox_detector.set(entry['detector'])

        self.entry_tokenPass.delete(0, tk.END)
        self.entry_tokenPass.insert(0, entry['files'].split(', ')[-1])

        self.spinbox_calibration.set(' G/P: {}'.format(entry['status'][0]))
        self.spinbox_tokenPass.set(' TP: {}'.format(entry['status'][-1]))

        self.place_record_group()

        self.combobox_boardLocation.event_generate('<<ComboboxSelected>>')

        self.update_bounds()

    def set_progress(self, i):
        self.progressBar_mainView['value'] = i
        self.progressBar_mainView.update()

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
        serial, qrcode, location, rack, crate, slot, det, comment = data

        query = 'WHERE serial = {}'.format(repr(serial))
        if len(self.squash.select(query)) > 0:
            self.set_notify_warning('{} already exists'.format(serial))
            return False

        query = 'WHERE id = {}'.format(repr(qrcode))
        if qrcode != '' and len(self.squash.select(query)) > 0:
            self.set_notify_warning('{} already exists'.format(qrcode))
            return False

        if location == 'BNL (sPHENIX)' and (not rack or
                                            not crate or
                                            not slot or
                                            not det):
            self.set_notify_warning('invalid rack/crate/slot/detector')
            return False

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
            'rack': rack,
            'crate': crate,
            'slot': slot,
            'detector': det,
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
        entry['rack'] = data['rack']
        entry['crate'] = data['crate']
        entry['slot'] = data['slot']
        entry['detector'] = data['detector']

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
        self.treeview_boardInfo.insert(
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
        self.treeview_boardInfo.delete(*self.treeview_boardInfo.get_children())

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

        p = re.compile('(.*) \[.*\] <.*>')

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

            self.treeview_boardInfo.insert('', tk.END, e_id, tags=e_tag, text=entry['serial'])

            self._insert(e_id, 'QR code', i_tag, entry['id'])
            self._insert(e_id, 'location', 'info', location[::-1])
            if p.match(location[-1]).group(1) == 'BNL (sPHENIX)':
                rcs = entry['detector'] + ': ' + ', '.join([
                    '{} {}'.format(x.upper(), entry[x])
                    for x in ('rack', 'crate', 'slot')
                ])
                self._insert(e_id, 'D: R/C/S', 'info', rcs)
            self._insert(e_id, 'history', 'info', history[::-1])
            self._insert(e_id, 'comment', 'info', comment[::-1])
            self._insert(e_id, 'status', s_tag, status)
            self._insert(e_id, f_info, [f_tag, 'info'], ['<expand>'] + files)
            self._insert(e_id, 'edit', 'edit', '', label='<edit>')

            self.set_progress(i * 100 / len(self.results))

    @Decorators.show_progress
    def modify_database_entry(self, data):
        qrcode, location, rack, crate, slot, det, comment, token, status = data

        if location == 'BNL (sPHENIX)' and (not rack or
                                            not crate or
                                            not slot or
                                            not det):
            self.set_notify_warning('invalid rack/crate/slot/detector')
            return False

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
        entry['rack'] = rack
        entry['crate'] = crate
        entry['slot'] = slot
        entry['detector'] = det

        condition = 'WHERE serial = {}'.format(repr(entry['serial']))

        self.squash.update(*zip(*entry.items()), condition)


if __name__ == '__main__':
    root = tk.Tk()
    interface = SquashInterface(root)
    root.mainloop()
