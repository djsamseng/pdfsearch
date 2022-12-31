

import typing

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level

ElemListType = typing.List[typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]]
BboxType = typing.Tuple[float, float, float, float]

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
    text = elem.get_text()
    if text != "\n" and text != " ":
      print("Unhandled LTAnno", elem)
    return None
  elif isinstance(elem, pdfminer.layout.LTCurve):
    return elem
  elif isinstance(elem, pdfminer.layout.LTLine):
    # LTLine and LTRect is a LTCurve
    print("Line:", elem.pts, elem.fill, elem.stroking_color, elem.stroke, elem.non_stroking_color, elem.evenodd, elem.linewidth)
    assert False, "Unhandled line:" + str(elem)
  elif isinstance(elem, pdfminer.layout.LTFigure):
    print("Unhandled LTFigure:", elem)
  else:
    print("Unhandled:", elem)
    assert False, "Unhandled elem:" + str(elem)

def get_underlying(page: typing.Iterable[pdfminer.layout.LTComponent]) -> ElemListType:
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

def filter_contains_bbox_hierarchical(elems: typing.Iterable[pdfminer.layout.LTComponent], bbox: BboxType) -> typing.List[pdfminer.layout.LTComponent]:
  out = []
  to_process: typing.List[pdfminer.layout.LTContainer] = []
  for elem in elems:
    if isinstance(elem, pdfminer.layout.LTAnno):
      continue
    if box_contains(outer=bbox, inner=elem.bbox):
      out.append(elem)
    elif isinstance(elem, pdfminer.layout.LTContainer):
      to_process.append(elem)

  while len(to_process) > 0:
    container = to_process.pop()
    for elem in container:
      if isinstance(elem, pdfminer.layout.LTAnno):
        continue
      if box_contains(outer=bbox, inner=elem.bbox):
        out.append(elem)
      elif isinstance(elem, pdfminer.layout.LTContainer):
        to_process.append(elem)

  return out
