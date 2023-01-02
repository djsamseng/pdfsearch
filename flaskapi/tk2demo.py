# -*- coding: utf-8 -*-
# Advanced zoom example. Like in Google Maps.
# It zooms only a tile, but not the whole image. So the zoomed tile occupies
# constant memory and not crams it with a huge resized image for the large zooms.
import random
import tkinter as tk
from tkinter import ttk

class AutoScrollbar(ttk.Scrollbar):
    ''' A scrollbar that hides itself if it's not needed.
        Works only if you use the grid geometry manager '''
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tk.TclError('Cannot use pack with this widget')

    def place(self, **kw):
        raise tk.TclError('Cannot use place with this widget')

class ZoomCanvas(ttk.Frame):
  '''
  page_width: int - width of the underlying canvas cropped to parent size
  page_height: int - height of the underlying canvas cropped to parent size
  '''
  def __init__(self, root, page_width: int, page_height: int):
      self.width = page_width
      self.height = page_height
      self.master = ttk.Frame(root)
      # Vertical and horizontal scrollbars for canvas
      vbar = AutoScrollbar(self.master, orient='vertical')
      hbar = AutoScrollbar(self.master, orient='horizontal')
      vbar.grid(row=0, column=1, sticky='ns')
      hbar.grid(row=1, column=0, sticky='we')
      # Create canvas and put image on it
      self.canvas = tk.Canvas(
        self.master,
        highlightthickness=0,
        xscrollcommand=hbar.set,
        yscrollcommand=vbar.set,
        bg="white")
      self.canvas.grid(row=0, column=0, sticky='nswe')
      self.canvas.update()  # wait till canvas is created
      vbar.configure(command=self.scroll_y)  # bind scrollbars to the canvas
      hbar.configure(command=self.scroll_x)
      # Bind events to the Canvas
      self.canvas.bind('<ButtonPress-1>', self.move_from)
      self.canvas.bind('<B1-Motion>',     self.move_to)
      self.canvas.bind('<MouseWheel>', self.wheel)  # with Windows and MacOS, but not Linux
      self.canvas.bind('<Button-5>',   self.wheel)  # only with Linux, wheel scroll down
      self.canvas.bind('<Button-4>',   self.wheel)  # only with Linux, wheel scroll up
      self.width, self.height = 2400, 1600
      self.imscale = 1.0  # scale for the canvaas image
      self.delta = 1.3  # zoom magnitude
      # Put image into container rectangle and use it to set proper coordinates to the image
      self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)
      # Plot some optional random rectangles for the test purposes
      minsize, maxsize, number = 5, 20, 10
      for n in range(number):
          x0 = random.randint(0, self.width - maxsize)
          y0 = random.randint(0, self.height - maxsize)
          x1 = x0 + random.randint(minsize, maxsize)
          y1 = y0 + random.randint(minsize, maxsize)
          color = ('red', 'orange', 'yellow', 'green', 'blue')[random.randint(0, 4)]
          self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, activefill='black')

  def scroll_y(self, *args, **kwargs):
      ''' Scroll canvas vertically and redraw the image '''
      self.canvas.yview(*args, **kwargs)  # scroll vertically

  def scroll_x(self, *args, **kwargs):
      ''' Scroll canvas horizontally and redraw the image '''
      self.canvas.xview(*args, **kwargs)  # scroll horizontally

  def move_from(self, event):
      ''' Remember previous coordinates for scrolling with the mouse '''
      self.canvas.scan_mark(event.x, event.y)

  def move_to(self, event):
      ''' Drag (move) canvas to the new position '''
      self.canvas.scan_dragto(event.x, event.y, gain=1)

  def wheel(self, event):
      ''' Zoom with mouse wheel '''
      x = self.canvas.canvasx(event.x)
      y = self.canvas.canvasy(event.y)
      bbox = self.canvas.bbox(self.container)  # get image area
      if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]: pass  # Ok! Inside the image
      else: return  # zoom only inside image area
      scale = 1.0
      # Respond to Linux (event.num) or Windows (event.delta) wheel event
      if event.num == 5 or event.delta == -120:  # scroll down
          i = min(self.width, self.height)
          if int(i * self.imscale) < 30: return  # image is less than 30 pixels
          self.imscale /= self.delta
          scale        /= self.delta
      if event.num == 4 or event.delta == 120:  # scroll up
          i = min(self.canvas.winfo_width(), self.canvas.winfo_height())
          if i < self.imscale: return  # 1 pixel is bigger than the visible area
          self.imscale *= self.delta
          scale        *= self.delta
      self.canvas.scale('all', x, y, scale, scale)  # rescale all canvas objects

  def grid(self, **kw):
        """ Put CanvasImage widget on the parent widget """
        self.master.grid(**kw)  # place CanvasImage widget on the grid
        self.master.grid(sticky='nswe')  # make frame container sticky
        self.master.rowconfigure(0, weight=1)  # make canvas expandable
        self.master.columnconfigure(0, weight=1)

class TkDrawerControlPanel:
  def __init__(self, root: tk.Tk, controls_width, controls_height) -> None:
    num_elements = 20
    height_needed = num_elements * 40

    self.frame = ttk.Frame(root)
    self.frame.grid(row=0, column=1, pady=(5,0), sticky="nw")
    self.frame.grid_rowconfigure(0, weight=1)
    self.frame.grid_columnconfigure(0, weight=1)
    self.frame.grid_propagate(False)

    self.canvas = tk.Canvas(
      master=self.frame
    )
    self.canvas.grid(row=0, column=0, sticky="news")
    self.vbar = ttk.Scrollbar(master=self.frame, orient='vertical', command=self.canvas.yview)
    self.vbar.grid(row=0, column=1, sticky="ns")

    self.canvas.configure(yscrollcommand=self.vbar.set)

    self.frame_buttons = tk.Frame(master=self.canvas)
    self.canvas.create_window((0, 0), window=self.frame_buttons, anchor="nw")
    self.container = self.canvas.create_rectangle((0, 0, controls_width, height_needed), width=0)

    for i in range(20):
      button = ttk.Button(master=self.frame_buttons, text="Button {0}".format(i))
      button.grid(row=i, column=0, sticky="news")

    self.frame_buttons.update_idletasks()

    self.frame.config(width=controls_width)
    self.canvas.config(scrollregion=self.canvas.bbox("all"))

    self.canvas.bind_all('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux
    self.canvas.bind_all('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
    self.canvas.bind_all('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up

  def grid(self, **kwargs):
    self.frame.grid(**kwargs)
    self.frame.grid(sticky="nswe")
    self.frame.rowconfigure(0, weight=1)
    self.frame.columnconfigure(0, weight=1)

  def outside(self, x, y):
    bbox = self.canvas.coords(self.container)
    if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
      return False
    return True

  def __wheel(self, event):
    x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
    y = self.canvas.canvasy(event.y)
    if self.outside(x, y):
      return
    if event.num == 5 or event.delta == -120: # scroll down
      self.canvas.yview_scroll(1, what="units")
    if event.num == 4 or event.delta == 120: # scroll up
      self.canvas.yview_scroll(-1, what="units")

class TkDrawerMainWindow(ttk.Frame):
  def __init__(self, root: tk.Tk, window_width, window_height, page_width, page_height):
    ttk.Frame.__init__(self, master=root)
    self.master.title("Pdf Drawer")
    self.master.geometry("{0}x{1}".format(window_width, window_height))
    self.master.rowconfigure(0, weight=1) # Expandable
    self.master.columnconfigure(0, weight=1)
    self.master.bind("<Key>", lambda event: self.master.after_idle(self.__keystroke, event))
    controlPanel = TkDrawerControlPanel(root=self.master, controls_width=100, controls_height=1_000)
    controlPanel.grid(row=0, column=1)
    canvas = ZoomCanvas(root=self.master, page_width=page_width, page_height=page_height)
    canvas.grid(row=0, column=0)

  def __keystroke(self, event):
    if event.keycode in [9]: # Esc
      self.master.destroy()

root = tk.Tk()
app = TkDrawerMainWindow(root=root, window_width=800, window_height=600, page_width=1600, page_height=1200)
app.mainloop()