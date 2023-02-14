
import collections
import typing

import tkinter as tk
from tkinter import ttk

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils

from . import pdfelemtransforms, path_utils
from .ltjson import LTJson, ElemListType, BboxType

class MousePositionTracker(tk.Frame):
    """ Tkinter Canvas mouse position widget. """

    def __init__(self, canvas, on_end):
        self.canvas = canvas
        self.canv_width = self.canvas.cget('width')
        self.canv_height = self.canvas.cget('height')
        self.reset()

        # Create canvas cross-hair lines.
        xhair_opts = dict(dash=(3, 2), fill='white', state=tk.HIDDEN)
        self.lines = (self.canvas.create_line(0, 0, 0, self.canv_height, **xhair_opts),
                      self.canvas.create_line(0, 0, self.canv_width,  0, **xhair_opts))
        self.on_end = on_end

    def cur_selection(self):
        return (self.start, self.end)

    def begin(self, event):
        self.hide()
        x, y = self.__get_x_y(event)
        self.start = (x, y)  # Remember position (no drawing).

    def update(self, event):
        x, y = self.__get_x_y(event)
        self.end = (x, y)
        self._update(event)
        self._command(self.start, (x, y))  # User callback.

    def _update(self, event):
        # Update cross-hair lines.
        x, y = self.__get_x_y(event)
        self.canvas.coords(self.lines[0], x, 0, x, self.canv_height)
        self.canvas.coords(self.lines[1], 0, y, self.canv_width, y)
        self.show()

    def __get_x_y(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        x = int(x)
        y = int(y)
        return x, y

    def reset(self):
        self.start = self.end = None

    def hide(self):
        self.canvas.itemconfigure(self.lines[0], state=tk.HIDDEN)
        self.canvas.itemconfigure(self.lines[1], state=tk.HIDDEN)

    def show(self):
        self.canvas.itemconfigure(self.lines[0], state=tk.NORMAL)
        self.canvas.itemconfigure(self.lines[1], state=tk.NORMAL)

    def autodraw(self, command=lambda *args: None):
        """Setup automatic drawing; supports command option"""
        self.reset()
        self._command = command
        self.canvas.bind("<Button-3>", self.begin)
        self.canvas.bind("<B3-Motion>", self.update)
        self.canvas.bind("<ButtonRelease-3>", self.quit)

    def quit(self, event):
        self.hide()  # Hide cross-hairs.
        self.on_end(self.cur_selection())
        self.reset()



class SelectionObject:
    """ Widget to display a rectangular area on given canvas defined by two points
        representing its diagonal.
    """
    def __init__(self, canvas, select_opts):
        # Create attributes needed to display selection.
        self.canvas = canvas
        self.select_opts1 = select_opts
        self.width = self.canvas.cget('width')
        self.height = self.canvas.cget('height')

        # Options for areas outside rectanglar selection.
        select_opts1 = self.select_opts1.copy()  # Avoid modifying passed argument.
        select_opts1.update(state=tk.HIDDEN)  # Hide initially.
        # Separate options for area inside rectanglar selection.
        select_opts2 = dict(dash=(2, 2), fill='', outline='red', state=tk.HIDDEN)

        # Initial extrema of inner and outer rectangles.
        imin_x, imin_y,  imax_x, imax_y = 0, 0,  1, 1
        omin_x, omin_y,  omax_x, omax_y = 0, 0,  self.width, self.height

        self.rects = (
            # Area *outside* selection (inner) rectangle.
            #self.canvas.create_rectangle(omin_x, omin_y,  omax_x, imin_y, **select_opts1),
            #self.canvas.create_rectangle(omin_x, imin_y,  imin_x, imax_y, **select_opts1),
            #self.canvas.create_rectangle(imax_x, imin_y,  omax_x, imax_y, **select_opts1),
            #self.canvas.create_rectangle(omin_x, imax_y,  omax_x, omax_y, **select_opts1),
            # Inner rectangle.
            self.canvas.create_rectangle(imin_x, imin_y,  imax_x, imax_y, **select_opts2),
        )

    def update(self, start, end):
        # Current extrema of inner and outer rectangles.
        imin_x, imin_y,  imax_x, imax_y = self._get_coords(start, end)
        omin_x, omin_y,  omax_x, omax_y = 0, 0,  self.width, self.height

        # Update coords of all rectangles based on these extrema.
        #self.canvas.coords(self.rects[0], omin_x, omin_y,  omax_x, imin_y),
        #self.canvas.coords(self.rects[1], omin_x, imin_y,  imin_x, imax_y),
        #self.canvas.coords(self.rects[2], imax_x, imin_y,  omax_x, imax_y),
        #self.canvas.coords(self.rects[3], omin_x, imax_y,  omax_x, omax_y),
        self.canvas.coords(self.rects[0], imin_x, imin_y,  imax_x, imax_y),

        for rect in self.rects:  # Make sure all are now visible.
            self.canvas.itemconfigure(rect, state=tk.NORMAL)

    def _get_coords(self, start, end):
        """ Determine coords of a polygon defined by the start and
            end points one of the diagonals of a rectangular area.
        """
        return (min((start[0], end[0])), min((start[1], end[1])),
                max((start[0], end[0])), max((start[1], end[1])))

    def hide(self):
        for rect in self.rects:
            self.canvas.itemconfigure(rect, state=tk.HIDDEN)

class AutoScrollbar(ttk.Scrollbar):
  '''
  A scrollbar that hides itself if it's not needed.
  Works only if you use the grid geometry manager
  '''
  def set(self, lo: float, hi: float):
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
  def __init__(
    self,
    root: tk.Tk,
    page_width: int,
    page_height: int,
    on_selection: typing.Callable[[typing.List[int]], None],
    select_intersection: bool,
  ):
    self.width = page_width
    self.height = page_height
    self.select_intersection = select_intersection
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
    self.width, self.height = page_width, page_height
    self.imscale = 1.0  # scale for the canvaas image
    self.delta = 1.3  # zoom magnitude
    # Put image into container rectangle and use it to set proper coordinates to the image
    self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)
    self.label_ids: typing.List[tk._CanvasItemId] = []
    self.item_ids: typing.List[typing.List[tk._CanvasItemId]] = []
    self.has_zoomed = False
    self.selection_obj = SelectionObject(self.canvas, dict(dash=(2,2), stipple="gray25", fill="", outline="red"))
    self.on_selection = on_selection
    def on_drag(start, end, **kwarg):
      self.selection_obj.update(start, end)
    def on_end(selection: path_utils.LinePointsType):
      if self.on_selection is not None:
        x0, y0, x1, y1 = selection
        if self.select_intersection:
          selected = self.canvas.find_overlapping(x0, y0, x1, y1)
        else:
          selected = self.canvas.find_enclosed(x0, y0, x1, y1)
        self.on_selection(selected)
    self.pos_tracker = MousePositionTracker(self.canvas, on_end=on_end)
    self.pos_tracker.autodraw(command=on_drag)

  def rot_point(self, x: float, y: float):
    return x, self.height - y

  def draw_path(
    self,
    wrapper: LTJson,
    color: str,
    xmin: int,
    ymin: int
  ):
    color = "black"
    line_points = wrapper.get_path_lines()
    line_ids: typing.List[tk._CanvasItemId] = []
    for line in line_points:
      x0, y0, x1, y1 = line
      x0, y0 = self.rot_point(x0-xmin, y0+ymin)
      x1, y1 = self.rot_point(x1-xmin, y1+ymin)
      line_id = self.canvas.create_line(x0, y0, x1, y1, fill=color)
      line_ids.append(line_id)
    return line_ids

  def draw_rect(self, box: typing.Tuple[float, float, float, float], color: str="black"):
    x0, y0, x1, y1 = box
    x0, y0 = self.rot_point(x0, y0)
    x1, y1 = self.rot_point(x1, y1)
    rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline=color)
    return [rect_id]

  def insert_text(self, pt: typing.Tuple[float, float], text: str, font_size:int=12, fill:str="black", upright:bool=True):
    x, y = pt
    x, y = self.rot_point(x, y)
    angle = 0 if upright else 90
    text_id = self.canvas.create_text(x, y, fill=fill, font=("Arial", font_size), text=text, angle=angle)
    return [text_id]

  def scroll_y(self, *args, **kwargs):
      ''' Scroll canvas vertically and redraw the image '''
      self.canvas.yview(*args, **kwargs)  # scroll vertically

  def scroll_x(self, *args, **kwargs):
      ''' Scroll canvas horizontally and redraw the image '''
      self.canvas.xview(*args, **kwargs)  # scroll horizontally

  def move_from(self, event):
      ''' Remember previous coordinates for scrolling with the mouse '''
      x = self.canvas.canvasx(event.x)
      y = self.canvas.canvasy(event.y)

      self.canvas.scan_mark(event.x, event.y)

  def move_to(self, event):
      ''' Drag (move) canvas to the new position '''
      self.canvas.scan_dragto(event.x, event.y, gain=1)

  def wheel(self, event):
      ''' Zoom with mouse wheel '''
      self.has_zoomed = True
      x = self.canvas.canvasx(event.x)
      y = self.canvas.canvasy(event.y)
      bbox = self.canvas.bbox(self.container)  # get image area
      #if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]: pass  # Ok! Inside the image
      #else: return  # zoom only inside image area
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

  def set_item_visibility(self, item_ids, visibility=None):
    for item_id in item_ids:
      if visibility is None:
        old_state = self.canvas.itemcget(item_id, "state")
        new_state = "normal" if old_state == "hidden" else "hidden"
      else:
        new_state = "normal" if visibility else "hidden"
      self.canvas.itemconfigure(item_id, state=new_state)

  def grid(self, **kw):
    """ Put CanvasImage widget on the parent widget """
    self.master.grid(**kw)  # place CanvasImage widget on the grid
    self.master.grid(sticky='nswe')  # make frame container sticky
    self.master.rowconfigure(0, weight=1)  # make canvas expandable
    self.master.columnconfigure(0, weight=1)

class TkDrawerControlPanel:
  def __init__(self, root: tk.Tk, controls_width: int, controls_height: int) -> None:
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
    self.hbar = ttk.Scrollbar(master=self.frame, orient="horizontal", command=self.canvas.xview)
    self.hbar.grid(row=0, column=0, sticky="ew")
    self.vbar = ttk.Scrollbar(master=self.frame, orient='vertical', command=self.canvas.yview)
    self.vbar.grid(row=0, column=1, sticky="ns")

    self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

    self.frame_buttons = tk.Frame(master=self.canvas)
    self.canvas.create_window((0, 0), window=self.frame_buttons, anchor="nw")
    self.container = self.canvas.create_rectangle((0, 0, controls_width, height_needed), width=0)

    self.buttons: typing.List[ttk.Button] = []

    self.frame.config(width=controls_width)

    self.canvas.bind_all('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux
    self.canvas.bind_all('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
    self.canvas.bind_all('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up

  def clear_buttons(self):
    for button in self.buttons:
      button.grid_forget()
      button.destroy()
    self.buttons = []

  def add_button(
    self,
    text: str,
    callback: typing.Union[typing.Callable[[],None], None] = None,
    on_enter_cb: typing.Union[typing.Callable[[],None], None] = None,
    on_leave_cb: typing.Union[typing.Callable[[],None], None] = None,
  ):
    def on_press():
      old_bg = button.cget("background")
      new_bg = "#d9d9d9" if old_bg == "white" else "white"
      button.config(background=new_bg)
      if callback is not None:
        callback()
    def on_enter(*args):
      if on_enter_cb is not None:
        on_enter_cb()
    def on_leave(*args):
      if on_leave_cb is not None:
        on_leave_cb()
    button = tk.Button(master=self.frame_buttons, text=text, command=on_press)
    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
    button.grid(row=len(self.buttons)+1, column=0, sticky="w")
    self.buttons.append(button)

  def finish_draw(self):
    self.frame_buttons.update_idletasks()
    self.canvas.config(scrollregion=self.canvas.bbox("all"))

  def grid(self, **kwargs):
    self.frame.grid(**kwargs)
    self.frame.grid(sticky="nswe")
    self.frame.rowconfigure(0, weight=1)
    self.frame.columnconfigure(0, weight=1)

  def outside(self, x: float, y: float):
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
  def __init__(
    self,
    root: tk.Tk,
    window_width: int,
    window_height: int,
    page_width: int,
    page_height: int,
    on_selection: typing.Callable[[typing.List[int]], None],
    select_intersection: bool,
  ):
    ttk.Frame.__init__(self, master=root)
    self.master.title("Pdf Drawer")
    self.master.geometry("{0}x{1}".format(window_width, window_height))
    self.master.rowconfigure(0, weight=1) # Expandable
    self.master.columnconfigure(0, weight=1)
    self.master.bind("<Key>", lambda event: self.master.after_idle(self.__keystroke, event))
    self.controlPanel = TkDrawerControlPanel(root=self.master, controls_width=300, controls_height=1_000)
    self.controlPanel.grid(row=0, column=1)
    self.canvas = ZoomCanvas(
      root=self.master,
      page_width=page_width,
      page_height=page_height,
      on_selection=on_selection,
      select_intersection=select_intersection
    )
    self.canvas.grid(row=0, column=0)

  def __keystroke(self, event):
    if event.keycode in [9]: # Esc
      self.master.destroy()

def pdfminer_class_name(elem: LTJson):
  if elem.is_container:
    return "Container"
  if elem.original_path is not None:
    return "Curve"
  if elem.text is not None:
    return "Text"
  return "Unknown" + str(elem.__dict__)

class TkDrawer:
  def __init__(self, width:int, height:int, select_intersection:bool = False) -> None:
    root = tk.Tk()
    self.page_width = width
    self.page_height = height
    self.app = TkDrawerMainWindow(
      root=root,
      window_width=1200,
      window_height=800,
      page_width=width,
      page_height=height,
      on_selection=self.on_selection,
      select_intersection=select_intersection,
    )
    self.id_to_elem: typing.Dict[int, LTJson] = {}
    self.selected_elems: typing.Dict[LTJson, bool] = {}

  def on_selection(
    self,
    line_ids: typing.List[int],
  ):
    self.app.controlPanel.clear_buttons()
    def on_save():
      for elem, selected in self.selected_elems.items():
        if selected:
          print(elem.bbox, elem.original_path)
    self.app.controlPanel.add_button(text="save", callback=on_save)
    elems: typing.DefaultDict[LTJson, typing.List[int]] = collections.defaultdict(list)
    self.selected_elems = {}
    for id in line_ids:
      if id in self.id_to_elem:
        elem = self.id_to_elem[id]
        elems[elem].append(id)
    for elem, ids in elems.items():
      self.selected_elems[elem] = True
      text = ""
      if elem.text is not None:
        text += elem.text.replace("\n", " ")
      def on_press(ids: typing.List[int]):
        for id in ids:
          elem = self.id_to_elem[id]
          self.selected_elems[elem] = not self.selected_elems[elem]
        self.app.canvas.set_item_visibility(ids)

      self.app.controlPanel.add_button(
        text="{0} {1} {2} {3}".format(text, pdfminer_class_name(elem), elem.bbox, elem.original_path),
        callback=lambda ids=ids: on_press(ids))
    self.app.controlPanel.finish_draw()


  def insert_container(
    self,
    elem: LTJson,
    parent_idx: typing.Union[int, None],
    xmin: int,
    ymin: int,
    draw_buttons: bool,
  ):
    x0, y0, x1, y1 = elem.bbox
    box = (x0-xmin, y0-ymin, x1-xmin, y1-ymin)
    ids = self.app.canvas.draw_rect(box=box)
    for id in ids:
      self.id_to_elem[id] = elem
    self.app.canvas.set_item_visibility(ids, visibility=False)
    text = ""
    if elem.text is not None:
      text += elem.text.replace("\n", " ")
    if draw_buttons:
      def on_enter():
        self.app.canvas.set_item_visibility(ids, visibility=True)
      def on_leave():
        self.app.canvas.set_item_visibility(ids, visibility=False)
      self.app.controlPanel.add_button(
        text="{0} {1} {2}".format(text, pdfminer_class_name(elem), box),
        on_enter_cb=on_enter,
        on_leave_cb=on_leave
      )
  def draw_path(
    self,
    wrapper: LTJson,
    parent_idx: typing.Union[int, None],
    xmin: int,
    ymin: int,
    draw_buttons: bool,
  ):

    ids = self.app.canvas.draw_path(wrapper=wrapper, color="black", xmin=xmin, ymin=ymin)
    for id in ids:
      self.id_to_elem[id] = wrapper
    text = ""
    text_idx = None
    if wrapper.text is not None:
      text += wrapper.text.replace("\n", " ")
      x0, y0, x1, y1 = wrapper.bbox
      font_size = 11
      text_ids = self.app.canvas.insert_text(pt=(x0-xmin, y1+ymin), text=text, font_size=int(font_size), upright=wrapper.upright)
    if draw_buttons:
      def on_press():
        self.app.canvas.set_item_visibility(ids)
        if text_ids is not None:
          self.app.canvas.set_item_visibility(text_ids)
      self.app.controlPanel.add_button(
        text="{0} {1} {2}".format(text, pdfminer_class_name(wrapper), wrapper.original_path),
        callback=on_press)
  def insert_text(
    self,
    elem: LTJson,
    parent_idx: typing.Union[int, None],
    xmin: int,
    ymin: int,
    draw_buttons: bool
  ):
    x0, y0, x1, y1 = elem.bbox
    text = elem.text or ""
    font_size = elem.size or 11
    # Size is closer to the rendered fontsize than fontsize is per https://github.com/pdfminer/pdfminer.six/issues/202
    # y1 because we flip the point on the y axis
    ids = self.app.canvas.insert_text(pt=(x0-xmin, y1+ymin), text=text, font_size=int(font_size), upright=elem.upright)
    for id in ids:
      self.id_to_elem[id] = elem
    if draw_buttons:
      def on_press():
        self.app.canvas.set_item_visibility(ids)
      self.app.controlPanel.add_button(
        text="{0} ({1},{2}) {3}".format(pdfminer_class_name(elem), x0, y0, text),
        callback=on_press)
  def show(self, name: str):
    self.app.controlPanel.finish_draw()
    self.app.mainloop()

  def draw_elems(self,
    elems: typing.Iterable[LTJson],
    align_top_left: bool=False,
    draw_buttons: bool=True,
    draw_all_text: bool=True):
    # Want to accept the hierarchy
    # If we get a container, we want to present the container in the control panel with its inner text
    # however when we draw we draw the underlying LTChar
    # When we select the container in the control panel we want to highlight the bbox
    # When sending to the client, we send the positions of what we found and how to draw it
    if align_top_left:
      xmin, ymin = self.get_minx_miny(wrappers=elems)
    else:
      xmin, ymin = 0, 0
    for wrapper in elems:
      if wrapper.is_container:
        # Children always come immediately after container so indentation will be underneath parent
        self.insert_container(elem=wrapper, parent_idx=wrapper.parent_idx, xmin=xmin, ymin=ymin, draw_buttons=draw_buttons)
        if draw_all_text and wrapper.text is not None:
          self.insert_text(elem=wrapper, parent_idx=wrapper.parent_idx, xmin=xmin, ymin=ymin, draw_buttons=draw_buttons)
      elif wrapper.original_path is not None and wrapper.linewidth is not None:
        if wrapper.linewidth > 0:
          self.draw_path(wrapper=wrapper, parent_idx=wrapper.parent_idx, xmin=xmin, ymin=ymin, draw_buttons=draw_buttons)
      elif wrapper.text is not None or wrapper.label is not None:
        if wrapper.text is None:
          wrapper.text = wrapper.label
        self.insert_text(elem=wrapper, parent_idx=wrapper.parent_idx, xmin=xmin, ymin=ymin, draw_buttons=draw_buttons)

      else:
        #pass
        print("Unhandled draw", wrapper)
        #assert False, "Unhandled draw" + str(elem)

  def draw_bbox(self, bbox: BboxType, color: str):
    _ = self.app.canvas.draw_rect(bbox, color)

  def get_minx_miny(self, wrappers: typing.Iterable[LTJson]):
    xmin = self.page_width
    ymax = 0
    for wrapper in wrappers:
      if wrapper.original_path is not None:
        x0, y0, x1, y1 = wrapper.bbox
        xmin = min(xmin, min(x0, x1))
        ymax = max(ymax, max(y0, y1))
    return int(xmin), self.page_height - int(ymax)


def get_awindows_key(window_schedule_elems: typing.Iterable[LTJson], page_width: int, page_height: int):
  y0, x0 = 1027, 971
  y1, x1 = 1043, 994
  bbox = (x0, page_height-y1, x1, page_height-y0)
  key_elems = pdfelemtransforms.filter_contains_bbox_hierarchical(elems=window_schedule_elems, bbox=bbox)
  return key_elems

def test_drawer():
  with np.load("./flaskapi/window_schedule_hierarchy.npz", allow_pickle=True) as f:
    window_schedule_elems, width, height = f["elems"], f["width"], f["height"]
    window_schedule_elems: ElemListType = window_schedule_elems
    width = int(width)
    height = int(height)

  window_schedule_wrappers = pdfelemtransforms.get_underlying_parent_links(elems=window_schedule_elems)

  drawer = TkDrawer(width=width, height=height)
  awindows_key = get_awindows_key(window_schedule_elems=window_schedule_wrappers, page_width=width, page_height=height)
  # debug_utils.print_elem_tree(elems=awindows_key)
  underlying = pdfelemtransforms.get_underlying_parent_links(window_schedule_elems)
  drawer.draw_elems(elems=underlying)
  drawer.show("A Windows Key")

if __name__ == "__main__":
  test_drawer()
