
import math

import tkinter as tk
from tkinter import ttk

def compute_bezier_points(vertices, numPoints=30):
  result = []

  b0x = vertices[0][0]
  b0y = vertices[0][1]
  b1x = vertices[1][0]
  b1y = vertices[1][1]
  b2x = vertices[2][0]
  b2y = vertices[2][1]
  b3x = vertices[3][0]
  b3y = vertices[3][1]

  # Compute polynomial coefficients from Bezier points
  ax = -b0x + 3 * b1x + -3 * b2x + b3x
  ay = -b0y + 3 * b1y + -3 * b2y + b3y

  bx = 3 * b0x + -6 * b1x + 3 * b2x
  by = 3 * b0y + -6 * b1y + 3 * b2y

  cx = -3 * b0x + 3 * b1x
  cy = -3 * b0y + 3 * b1y

  dx = b0x
  dy = b0y

  # Set up the number of steps and step size
  numSteps = numPoints - 1 # arbitrary choice
  h = 1.0 / numSteps # compute our step size

  # Compute forward differences from Bezier points and "h"
  pointX = dx
  pointY = dy

  firstFDX = ax * (h * h * h) + bx * (h * h) + cx * h
  firstFDY = ay * (h * h * h) + by * (h * h) + cy * h


  secondFDX = 6 * ax * (h * h * h) + 2 * bx * (h * h)
  secondFDY = 6 * ay * (h * h * h) + 2 * by * (h * h)

  thirdFDX = 6 * ax * (h * h * h)
  thirdFDY = 6 * ay * (h * h * h)

  # Compute points at each step
  result.append((int(pointX), int(pointY)))

  for i in range(numSteps):
      pointX += firstFDX
      pointY += firstFDY

      firstFDX += secondFDX
      firstFDY += secondFDY

      secondFDX += thirdFDX
      secondFDY += thirdFDY

      result.append((int(pointX), int(pointY)))

  return result

class AutoScrollbar(ttk.Scrollbar):
  '''
  A scrollbar that hides itself if it's not needed.
  Works only if you use the grid geometry manager
  '''
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
      bg="white",
      border=1,
      borderwidth=1
    )
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
    self.label_ids = []

  def rot_point(self, x, y):
    return x, self.height - y

  def draw_path(self, path, color):
    x, y = 0, 0
    x_start, y_start = x, y
    color = "black"
    for pt in path:
      if pt[0] == 'm':
        x, y = pt[1]
        x, y = self.rot_point(x, y)
        x_start, y_start = x, y
      elif pt[0] == 'l':
        x2, y2 = pt[1]
        x2, y2 = self.rot_point(x2, y2)
        self.canvas.create_line(x, y, x2, y2, fill=color)
        x, y = x2, y2
      elif pt[0] == 'c':
        (x2, y2), (x3, y3), (x4, y4) = pt[1:]
        x2, y2 = self.rot_point(x2, y2)
        x3, y3 = self.rot_point(x3, y3)
        x4, y4 = self.rot_point(x4, y4)
        bezier_points = compute_bezier_points(vertices=[(x, y), (x2, y2), (x3, y3), (x4, y4)])
        for idx in range(1, len(bezier_points)):
          xstart, ystart = bezier_points[idx-1]
          xend, yend = bezier_points[idx]
          self.canvas.create_line(xstart, ystart, xend, yend, fill=color)
        x, y = x4, y4
      elif pt[0] == 'h':
        self.canvas.create_line(x, y, x_start, y_start, fill=color)

  def insert_text(self, pt, text, font_size=12):
    x, y = pt
    x, y = self.rot_point(x, y)
    text_id = self.canvas.create_text(x, y, fill="black", font=("Arial", font_size), text=text)
    self.label_ids.append((text_id, font_size))


  def unused(self):
    import random
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
      if event.num == 5 or event.delta == -120:  # scroll down (text getssmaller)
          i = min(self.width, self.height)
          if int(i * self.imscale) < 30: return  # image is less than 30 pixels
          self.imscale /= self.delta
          scale        /= self.delta
          self.scale_font()
      if event.num == 4 or event.delta == 120:  # scroll up
          i = min(self.canvas.winfo_width(), self.canvas.winfo_height())
          if i < self.imscale: return  # 1 pixel is bigger than the visible area
          self.imscale *= self.delta
          scale        *= self.delta
          self.scale_font()
      self.canvas.scale('all', x, y, scale, scale)  # rescale all canvas objects

  def scale_font(self):
    for label_id, orig_font_size in self.label_ids:
      new_font_size = int(self.imscale * orig_font_size)
      self.canvas.itemconfigure(label_id, {
        "font": ("Arial", new_font_size)
      })

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
    self.canvas = ZoomCanvas(root=self.master, page_width=page_width, page_height=page_height)
    self.canvas.grid(row=0, column=0)

  def __keystroke(self, event):
    if event.keycode in [9]: # Esc
      self.master.destroy()

class TkDrawer:
  def __init__(self, width:int, height:int) -> None:
    root = tk.Tk()
    self.app = TkDrawerMainWindow(root=root, window_width=800, window_height=600, page_width=width, page_height=height)
  def draw_path(self, *args, **kwargs):
    self.app.canvas.draw_path(*args, **kwargs)
  def insert_text(self, *args, **kwargs):
    self.app.canvas.insert_text(*args, **kwargs)
  def show(self, name, callback=None):
    self.app.mainloop()
