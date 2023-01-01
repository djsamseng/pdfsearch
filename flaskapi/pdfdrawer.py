

import cv2
import numpy as np
import fitz
import pdfminer
import pygame
import pyglet # pip install pyglet==1.5.27

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

class PygameDraw():
  def __init__(self, width, height) -> None:
    pygame.init()
    self.draw_width = width
    self.draw_height = height
    self.screen = pygame.display.set_mode((width*0.6, height/2))
    self.surface = pygame.Surface(size=(width, height))
    self.camera_rect = self.screen.get_rect().copy()
    self.scale = 1.0
    self.surface.fill(color=(255,255,255))
    self.paths = []
    self.texts = []

  def rot_point(self, x, y):
    x = self.screen.get_width() - x
    return x, y

  def draw_path(self, path, color=(255, 0, 0)):
    self.paths.append((path, color))
    self.draw_path_impl(path=path, color=color, scale=self.scale)

  def draw_path_impl(self, path, color, scale):
    color = (255, 0, 0)
    x, y = 0, 0
    x_start, y_start = x, y
    for pt in path:
      if pt[0] == "m":
        x, y = pt[1]
        x, y = self.rot_point(x, y)
        x_start, y_start = x, y
      elif pt[0] == "l":
        x2, y2 = pt[1]
        x2, y2 = self.rot_point(x2, y2)
        pygame.draw.line(surface=self.surface, color=color, start_pos=(x*scale, y*scale), end_pos=(x2*scale, y2*scale))
        x, y = x2, y2
      elif pt[0] == "c":
        (x2, y2), (x3, y3), (x4, y4) = pt[1:]
        x2, y2 = self.rot_point(x2, y2)
        x3, y3 = self.rot_point(x3, y3)
        x4, y4 = self.rot_point(x4, y4)
        self.draw_bezier(pts=[(x*scale,y*scale), (x2*scale,y2*scale), (x3*scale,y3*scale), (x4*scale,y4*scale)], color=color)
      elif pt[0] == "h":
        pygame.draw.line(surface=self.surface, color=color, start_pos=(x*scale, y*scale), end_pos=(x_start*scale, y_start*scale))

  def insert_text(self, pt, text):
    pass

  def draw_bezier(self, pts=[(0,0), (0,0), (0,0), (0,0)], color=(255, 0, 0)):
    bezier_points = compute_bezier_points(pts)
    pygame.draw.lines(surface=self.surface, color=color, closed=False, points=bezier_points)

  def show(self, name, callback=None):
    clock = pygame.time.Clock()
    running = True
    while running:
      for evt in pygame.event.get():
        if evt.type == pygame.QUIT:
          running = False
        elif evt.type == pygame.KEYDOWN:
          if evt.key == pygame.K_ESCAPE:
            running = False
        elif evt.type == pygame.MOUSEMOTION:
          if pygame.mouse.get_pressed()[0]:
            percent_x = evt.pos[0] / self.screen.get_rect().width
            self.camera_rect.x = percent_x * (self.surface.get_rect().width - self.screen.get_rect().width)
            percent_y = evt.pos[1] / self.screen.get_rect().height
            self.camera_rect.y = percent_y * (self.surface.get_rect().height - self.screen.get_rect().height)
      self.screen.fill((255, 255, 255))
      self.screen.blit(self.surface, (self.camera_rect.x, self.camera_rect.y))
      pygame.display.flip()
      clock.tick(100)

ZOOM_IN_FACTOR = 1.2
ZOOM_OUT_FACTOR = 1/ZOOM_IN_FACTOR

class PygletDrawApp(pyglet.window.Window):
  def __init__(self, window_width, window_height, page_width, page_height, *args, **kwargs):
    conf = pyglet.gl.Config(sample_buffers=1,
      samples=4,
      depth_size=16,
      double_buffer=True)
    super().__init__(window_width, window_height, config=conf, resizable=True, *args, **kwargs)

    self.left = 0
    self.right = window_width
    self.bottom = 0
    self.top = window_height
    self.zoom_level = 1 # min(window_height / page_height, window_width / page_width) # Zoom out to see everything
    self.zoomed_width = window_width
    self.zoomed_height = window_height

    self.draw_batch = pyglet.graphics.Batch()

  def on_draw(self):
    # Initialize Projection matrix
    pyglet.gl.glMatrixMode( pyglet.gl.GL_PROJECTION )
    pyglet.gl.glLoadIdentity()
    # Initialize Modelview matrix
    pyglet.gl.glMatrixMode( pyglet.gl.GL_MODELVIEW )
    pyglet.gl.glLoadIdentity()
    # Save the default modelview matrix
    pyglet.gl.glPushMatrix()
    # Clear window with ClearColor
    pyglet.gl.glClear( pyglet.gl.GL_COLOR_BUFFER_BIT )
    # Set orthographic projection matrix
    pyglet.gl.glOrtho( self.left, self.right, self.bottom, self.top, 1, -1 )

    self.draw_batch.draw()

    # Remove default modelview matrix
    pyglet.gl.glPopMatrix()

  def on_resize(self, width, height):
    self.__init_gl(width=width, height=height)

  def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
    self.left   -= dx*self.zoom_level
    self.right  -= dx*self.zoom_level
    self.bottom -= dy*self.zoom_level
    self.top    -= dy*self.zoom_level

  def on_mouse_scroll(self, x, y, dx, dy):
    # Get scale factor
    f = ZOOM_IN_FACTOR if dy > 0 else ZOOM_OUT_FACTOR if dy < 0 else 1
    # If zoom_level is in the proper range
    if .2 < self.zoom_level*f < 5:
      self.zoom_level *= f

      mouse_x = x/self.width
      mouse_y = y/self.height

      mouse_x_in_world = self.left   + mouse_x*self.zoomed_width
      mouse_y_in_world = self.bottom + mouse_y*self.zoomed_height

      self.zoomed_width  *= f
      self.zoomed_height *= f

      self.left   = mouse_x_in_world - mouse_x*self.zoomed_width
      self.right  = mouse_x_in_world + (1 - mouse_x)*self.zoomed_width
      self.bottom = mouse_y_in_world - mouse_y*self.zoomed_height
      self.top    = mouse_y_in_world + (1 - mouse_y)*self.zoomed_height

  def update(self):
    pass

  def run(self):
    pyglet.app.run()

  def __init_gl(self, width, height):
    # Set clear color
    pyglet.gl.glClearColor(255/255, 255/255, 255/255, 255/255)
    # Set antialiasing
    pyglet.gl.glEnable( pyglet.gl.GL_LINE_SMOOTH )
    pyglet.gl.glEnable( pyglet.gl.GL_POLYGON_SMOOTH )
    pyglet.gl.glHint( pyglet.gl.GL_LINE_SMOOTH_HINT, pyglet.gl.GL_NICEST )

    # Set alpha blending
    pyglet.gl.glEnable( pyglet.gl.GL_BLEND )
    pyglet.gl.glBlendFunc( pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA )

    # Set viewport
    pyglet.gl.glViewport( 0, 0, width, height )
class PygletDraw():
  def __init__(self, width, height) -> None:
    self.page_width = width
    self.page_height = height
    self.app = PygletDrawApp(window_width=800, window_height=600, page_width=width, page_height=height)
    label = pyglet.text.Label("Hello!", font_size=36, color=(0,0,0,255), batch=self.app.draw_batch)
    self.draw_color = (0, 0, 0)

  def draw_path(self, path, color):
    color = self.draw_color
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
        line = pyglet.shapes.Line(x=x, y=y, x2=x2, y2=y2, color=color, batch=self.app.draw_batch)
        x, y = x2, y2
      elif pt[0] == 'c':
        (x2, y2), (x3, y3), (x4, y4) = pt[1:]
        x2, y2 = self.rot_point(x2, y2)
        x3, y3 = self.rot_point(x3, y3)
        x4, y4 = self.rot_point(x4, y4)
        #shape.draw_bezier(p1=(x, y), p2=(x2, y2), p3=(x3, y3), p4=(x4, y4))
        x, y = x4, y4
      elif pt[0] == 'h':
        line = pyglet.shapes.Line(x=x, y=y, x2=x_start, y2=y_start, color=color, batch=self.app.draw_batch)

  def insert_text(self, pt, text):
    x, y = pt
    label = pyglet.text.Label(text=text, font_size=12, x=x, y=y, color=(0, 0, 0, 255), batch=self.app.draw_batch)

  def rot_point(self, x, y):
    x = self.page_width - x
    #y = self.page.rect.height - y
    return x, y
  def show(self, name):
    pyglet.app.run()


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