
import io
import types
import typing

import numpy as np
import werkzeug.datastructures
import pdfminer, pdfminer.high_level, pdfminer.layout # miner.six

ElemListType = typing.List[typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]]
BboxType = typing.Tuple[float, float, float, float]

class DrawPath:
  currX: float
  currY: float
  prevX: float
  prevY: float
  def __init__(self, obj):
    self.currX = obj["currX"]
    self.currY = obj["currY"]
    self.prevX = obj["prevX"]
    self.prevY = obj["prevY"]

class SerializedLTCurve:
  path: typing.Union[typing.List[pdfminer.layout.PathSegment], None]
  bbox: BboxType
  def __init__(self, path: typing.Union[typing.List[pdfminer.layout.PathSegment], None], bbox: BboxType) -> None:
    self.path = path
    self.bbox = bbox

class SerializedLTChar:
  x0: float
  y0: float
  x1: float
  y1: float
  char: str
  bbox: BboxType
  def __init__(self, x0: float, y0: float, x1: float, y1: float, char: str, bbox: BboxType) -> None:
    self.x0 = x0
    self.y0 = y0
    self.x1 = x1
    self.y1 = y1
    self.char = char
    self.bbox = bbox

def find_shapes_in_drawpaths(pdfFile: werkzeug.datastructures.FileStorage, drawPaths: typing.List[DrawPath], pageNumber: int):
  pdfBytes = io.BytesIO(pdfFile.read())
  page_number = pageNumber - 1
  page_gen = pdfminer.high_level.extract_pages(pdf_file=pdfBytes, page_numbers=[page_number])
  pages = list(page_gen)
  if len(pages) > 0:
    page = pages[0]
  else:
    print("Failed to load pages:", len(pages))
    return [], 0, 0

  print("Looking on page:", page_number)
  return find_shapes_in_drawpaths_for_page(page=page, drawpaths=drawPaths)

def find_shapes_in_drawpaths_for_page(page: pdfminer.layout.LTPage, drawpaths: typing.List[DrawPath]):
  pathminx, pathmaxx, pathminy, pathmaxy = get_drawpaths_bounds(drawpaths=drawpaths)
  search_bbox = get_bbox(page=page, xleft=pathminx, xright=pathmaxx, ytop=pathminy, ybottom=pathmaxy)
  print("Looking in bbox:", search_bbox)
  pdfelems = get_underlying(page=page)
  found_elems = filter_contains_bbox(elems=pdfelems, bbox=search_bbox)
  # TODO: Return unaltered found_elems for searching similar on next request
  serialized = serialize_pdfminer_layout_types(found_elems)
  flipped_serialized = flip_ud_elems(elems=serialized, pageWidth=page.width, pageHeight=page.height)
  serialized = zero_align_elems(elems=serialized)
  flipped_serialized = zero_align_elems(elems=flipped_serialized)
  serialized = [ s.__dict__ for s in serialized ]
  flipped_serialized = [s.__dict__ for s in flipped_serialized ]
  return flipped_serialized, serialized

def zero_align_elems(elems: typing.Union[SerializedLTChar, SerializedLTCurve]):
  if len(elems) == 0:
    return elems
  x0, y0, x1, y1 = elems[0].bbox
  minx = min(x0, x1)
  miny = min(y0, y1)
  for elem in elems:
    x0, y0, x1, y1 = elem.bbox
    minx = min(minx, min(x0, x1))
    miny = min(miny, min(y0, y1))
  for elem in elems:
    if isinstance(elem, SerializedLTCurve):
      new_path = []
      for point in elem.path:
        x = point[1][0]
        y = point[1][1]
        new_path.append([ point[0], [ x-minx, y-miny ] ])
      elem.path = new_path
      x0, y0, x1, y1 = elem.bbox
      elem.bbox = (x0-minx, y0-miny, x1-minx, y1-miny)
    elif isinstance(elem, SerializedLTChar):
      elem.x0 -= minx
      elem.x1 -= minx
      elem.y0 -= miny
      elem.y1 -= miny
      x0, y0, x1, y1 = elem.bbox
      elem.bbox = (x0-minx, y0-miny, x1-minx, y1-miny)
    else:
      assert False, "Unhandled elem" + str(elem)
  return elems

def flip_ud_elem(elem: typing.Union[SerializedLTChar, SerializedLTCurve], pageWidth: int, pageHeight: int):
  if isinstance(elem, SerializedLTCurve):
    new_path = []
    for point in elem.path:
      if point[0] == "m" or point[0] == "l":
        x = point[1][0]
        y = point[1][1]
        new_path.append([ point[0], [ x, pageHeight - y ]])
      else:
        assert False, "Unhandled point in path:" + str(point)
    x0, y0, x1, y1 = elem.bbox
    bbox = (x0, pageHeight - y1, x1, pageHeight - y0)
    return SerializedLTCurve(path=new_path, bbox=bbox)
  elif isinstance(elem, SerializedLTChar):
    x0, y0, x1, y1 = elem.bbox
    bbox = (x0, pageHeight - y1, x1, pageHeight - y0)
    return SerializedLTChar(x0=elem.x0, y0=pageHeight-elem.y1, x1=elem.x1, y1=pageHeight-elem.y0, char=elem.char, bbox=bbox)
  else:
    assert False, "Unhandled elem in flip_ud_elem" + str(elem)

def flip_ud_elems(elems: typing.List[typing.Union[SerializedLTChar, SerializedLTCurve]], pageWidth: int, pageHeight: int):
  return [flip_ud_elem(elem=elem, pageWidth=pageWidth, pageHeight=pageHeight) for elem in elems]

def serialize_pdfminer_elem(elem: typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]):
  if isinstance(elem, pdfminer.layout.LTCurve):
    return SerializedLTCurve(path=elem.original_path, bbox=elem.bbox)
  elif isinstance(elem, pdfminer.layout.LTChar):
    return SerializedLTChar(x0=elem.x0, y0=elem.y0, x1=elem.x1, y1=elem.y1, char=elem.get_text(), bbox=elem.bbox)
  else:
    assert False, "Unhandled element in serialization:" + str(elem)

def serialize_pdfminer_layout_types(elems: ElemListType) -> typing.List[typing.Union[SerializedLTChar, SerializedLTCurve]]:
  return [serialize_pdfminer_elem(elem) for elem in elems]

def get_elems_bounds(elems: ElemListType):
  if len(elems) == 0:
    return 0, 0, 0, 0
  minx = elems[0].bbox[0]
  miny = elems[0].bbox[1]
  maxx = elems[0].bbox[2]
  maxy = elems[0].bbox[3]
  for elem in elems:
    x0, y0, x1, y1 = elem.bbox
    minx = min(minx, x0)
    maxx = max(maxx, x1)
    miny = min(miny, y0)
    maxy = max(maxy, y1)
    assert x0 <= x1, "x0 {0} not < x1 {1}".format(x0, x1)
    assert y0 <= y1, "y0 {0} not < y1 {1}".format(y0, y1)
  return minx, miny, maxx, maxy

def get_drawpaths_bounds(drawpaths: typing.List[DrawPath]):
  # x = [left=0, right=+]
  # y = [top=0, bottom=+]
  if len(drawpaths) == 0:
    return 0, 0, 0, 0
  minx = drawpaths[0].currX
  miny = drawpaths[0].currY
  maxx = drawpaths[0].currX
  maxy = drawpaths[0].currY
  for path in drawpaths:
    minx = min(minx, min(path.currX, path.prevX))
    maxx = max(maxx, max(path.currX, path.prevX))
    miny = min(miny, min(path.currY, path.prevY))
    maxy = max(maxy, max(path.currY, path.prevY))
  return (minx, maxx, miny, maxy)

def get_bbox(page: pdfminer.layout.LTPage, xleft:float, xright:float, ytop:float, ybottom:float):
  y0 = page.height - ytop
  y1 = page.height - ybottom
  return (xleft, y1, xright, y0)

def extend_out_if_element(out: ElemListType, elem: typing.Union[None, list, pdfminer.layout.LTCurve, pdfminer.layout.LTChar]):
  if elem == None:
    return
  elif isinstance(elem, list):
    out.extend(elem)
  elif isinstance(elem, pdfminer.layout.LTCurve):
    out.append(elem)
  elif isinstance(elem, pdfminer.layout.LTChar):
    out.append(elem)
  else:
    print("Unhandled extend:", elem)

def get_underlying_from_element(elem: pdfminer.layout.LTComponent) -> typing.Union[None, list, pdfminer.layout.LTCurve, pdfminer.layout.LTChar]:
  if isinstance(elem, pdfminer.layout.LTTextLineHorizontal):
    out = []
    for sub_elem in elem:
      extend_out_if_element(out=out, elem=get_underlying_from_element(sub_elem))
    return out
  elif isinstance(elem, pdfminer.layout.LTTextBoxHorizontal):
    out = []
    for sub_elem in elem:
      extend_out_if_element(out=out, elem=get_underlying_from_element(sub_elem))
    return out
  elif isinstance(elem, pdfminer.layout.LTTextContainer):
    print(elem)
    assert False, "Unhandled LTTextContainer" + str(elem)
  elif isinstance(elem, pdfminer.layout.LTChar):
    return elem
  elif isinstance(elem, pdfminer.layout.LTAnno):
    return None
  elif isinstance(elem, pdfminer.layout.LTCurve):
    return elem
  elif isinstance(elem, pdfminer.layout.LTLine):
    # LTLine and LTRect is a LTCurve
    print("Line:", elem.pts, elem.fill, elem.stroking_color, elem.stroke, elem.non_stroking_color, elem.evenodd, elem.linewidth)
    assert False, "Unhandled line:" + str(elem)
  else:
    print("Unhandled:", elem)
    assert False, "Unhandled elem:" + str(elem)

def get_underlying(page: pdfminer.layout.LTPage) -> ElemListType:
  out: ElemListType = []
  for elem in page:
    extend_out_if_element(out=out, elem=get_underlying_from_element(elem=elem))
  return out

def box_contains(outer: BboxType, inner: BboxType):
  x0a, y0a, x1a, y1a = outer
  x0b, y0b, x1b, y1b = inner
  if x0a <= x0b and y0a <= y0b:
    # outer starts before inner
    if x1a >= x1b and y1a >= y1b:
      # outer ends after inner
      return True
  return False

def filter_contains_bbox(elems: ElemListType, bbox: BboxType) -> ElemListType:
  out = []
  for elem in elems:
    if box_contains(outer=bbox, inner=elem.bbox):
      out.append(elem)
  return out

### Testing code

def test_extract():
  page_gen = pdfminer.high_level.extract_pages(pdf_file="../plan.pdf", page_numbers=[4])
  pages = list(page_gen)
  page = pages[0]
  with np.load("drawpaths.npz", allow_pickle=True) as f:
    drawpaths = f["drawPaths"]
    drawpaths = [DrawPath(p) for p in drawpaths]
  # drawpaths[0].currX == drawpaths[1].prevX
  # drawpaths[1].prevX draws line to drawpaths[1].currX
  # 1. find min and max of drawpaths
  # 2. find elements in pdf where bbox is inside min and max
  # 3. hit test?
  found_elems, pathminx, pathminy = find_shapes_in_drawpaths_for_page(page=page, drawpaths=drawpaths)
  print(found_elems)

if __name__ == "__main__":
  test_extract()
