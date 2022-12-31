

import cv2
import numpy as np
import fitz
import pdfminer

from pdfextracter import ElemListType

def imshow(name, im, mouse_callback=None):
  cv2.namedWindow(name, cv2.WINDOW_NORMAL)
  param = {
    "zoom_x": 1.,
    "zoom_y": 1.,
    "mouse_down": False
  }
  def handle_mouse(evt, x, y, flags, param):
    if evt == cv2.EVENT_MOUSEWHEEL or evt == cv2.EVENT_MOUSEHWHEEL:
      im_now = cv2.resize(im, dsize=None, fx=param["zoom_x"], fy=param["zoom_y"])
      cv2.imshow(name, im_now)
    elif evt == cv2.EVENT_LBUTTONDOWN:
      print("Click y={0} x={1}".format(y, x))
      param["mouse_down"] = True
    elif evt == cv2.EVENT_LBUTTONUP:
      param["mouse_down"] = False
    elif evt == cv2.EVENT_MOUSEMOVE:
      pass

  if mouse_callback is not None:
    cv2.setMouseCallback(name, mouse_callback)
  else:
    cv2.setMouseCallback(name, handle_mouse, param=param)
  cv2.imshow(name, im)

class FitzDraw():
  def __init__(self, width, height) -> None:
    self.pdf = fitz.open()
    self.page = self.pdf.new_page(width=width, height=height)
    self.page.set_rotation(0)

  def rot_point(self, x, y):
    x = self.page.rect.width - x
    #y = self.page.rect.height - y
    return x, y

  def draw_path(self, path, color):
    shape = self.page.new_shape()
    x, y = 0, 0
    x_start, y_start = x, y
    for pt in path:
      if pt[0] == 'm':
        x, y = pt[1]
        x, y = self.rot_point(x, y)
        x_start, y_start = x, y
      elif pt[0] == 'l':
        x2, y2 = pt[1]
        x2, y2 = self.rot_point(x2, y2)
        shape.draw_line(p1=(x, y), p2=(x2, y2))
        x, y = x2, y2
      elif pt[0] == 'c':
        (x2, y2), (x3, y3), (x4, y4) = pt[1:]
        x2, y2 = self.rot_point(x2, y2)
        x3, y3 = self.rot_point(x3, y3)
        x4, y4 = self.rot_point(x4, y4)
        shape.draw_bezier(p1=(x, y), p2=(x2, y2), p3=(x3, y3), p4=(x4, y4))
        x, y = x4, y4
      elif pt[0] == 'h':
        shape.draw_line(p1=(x, y), p2=(x_start, y_start))
    shape.finish(color=color, closePath=False)
    shape.commit()

  def insert_text(self, pt, text):
    # Each letter needs to be flipped up down if rotate=0 or left right if rotate=180 which isn't possible because the flip needs
    # to be local ie the letter positioning cannot change
    x, y = pt
    x, y = self.rot_point(x, y)
    self.page.insert_text((x, y), text, fontname="helv", fontsize=11, rotate=180)

  def show(self, name, callback=None):
    out_pix = self.page.get_pixmap()
    # out_pil = PIL.Image.frombytes("RGB", [out_pix.width, out_pix.height], out_pix.samples)
    out_np = np.frombuffer(buffer=out_pix.samples, dtype=np.uint8).reshape((out_pix.height, out_pix.width, -1))
    out_np = np.rot90(out_np)
    out_np = np.rot90(out_np)
    # out_np = np.flipud(out_np)
    # out_pil.show()
    imshow(name, out_np, mouse_callback=callback)

def draw_elems(elems: ElemListType, drawer: FitzDraw):
  for elem in elems:
    if isinstance(elem, pdfminer.layout.LTChar):
      x0, y0, x1, y1 = elem.bbox
      text = elem.get_text()
      drawer.insert_text(pt=(x0, y0), text=text)
    elif isinstance(elem, pdfminer.layout.LTCurve):
      if elem.linewidth > 0:
        drawer.draw_path(path=elem.original_path, color=elem.stroking_color)
    else:
      print("Unhandled draw", elem)
      assert False, "Unhandled draw" + str(elem)

def waitKey(code:int):
  cv2.waitKey(code)