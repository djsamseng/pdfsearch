
import io
import types
import typing

import numpy as np
import werkzeug.datastructures
import pdfminer, pdfminer.high_level, pdfminer.layout # miner.six

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

ElemListType = typing.List[typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]]

def find_shapes_in_drawpaths(pdfFile: werkzeug.datastructures.FileStorage, drawPaths: typing.List[DrawPath], pageNumber: int):
  pdfBytes = io.BytesIO(pdfFile.read())
  print(pageNumber, type(pageNumber))
  page_gen = pdfminer.high_level.extract_pages(pdf_file=pdfBytes, page_numbers=[pageNumber])
  pages = list(page_gen)
  if len(pages) > 0:
    page = pages[0]
  else:
    print("Failed to load pages:", len(pages))
    return []

  found_shapes = find_shapes_in_drawpaths_for_page(page=page, drawpaths=drawPaths)
  return found_shapes

def find_shapes_in_drawpaths_for_page(page: pdfminer.layout.LTPage, drawpaths: typing.List[DrawPath]):
  pathminx, pathmaxx, pathminy, pathmaxy = get_drawpaths_bounds(drawpaths=drawpaths)
  search_bbox = get_bbox(page=page, xleft=pathminx, xright=pathmaxx, ytop=pathminy, ybottom=pathmaxy)
  pdfelems = get_underlying(page=page)
  found_elems = filter_contains_bbox(elems=pdfelems, bbox=search_bbox)
  return serialize_pdfminer_layout_types(found_elems)

def serialize_pdfminer_elem(elem: typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]):
  if isinstance(elem, pdfminer.layout.LTCurve):
    return {
      "path": elem.original_path,
    }
  elif isinstance(elem, pdfminer.layout.LTChar):
    return {
      "x": elem.x0,
      "y": elem.y0,
      "char": elem.get_text()
    }
  else:
    print("Unhandled element in serialization:", elem)
  return {}

def serialize_pdfminer_layout_types(elems: ElemListType):
  return [serialize_pdfminer_elem(elem) for elem in elems]

def get_drawpaths_bounds(drawpaths: typing.List[DrawPath]):
  # x = [left=0, right=+]
  # y = [top=0, bottom=+]
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

def box_contains(outer, inner):
  x0a, y0a, x1a, y1a = outer
  x0b, y0b, x1b, y1b = inner
  if x0a <= x0b and y0a <= y0b:
    # outer starts before inner
    if x1a >= x1b and y1a >= y1b:
      # outer ends after inner
      return True
  return False

def filter_contains_bbox(elems: typing.List[pdfminer.layout.LTComponent], bbox) -> typing.List[pdfminer.layout.LTComponent]:
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
  found_elems = find_shapes_in_drawpaths_for_page(page=page, drawpaths=drawpaths)
  print(found_elems)

if __name__ == "__main__":
  test_extract()
