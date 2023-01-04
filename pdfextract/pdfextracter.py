

import typing

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level

ElemListType = typing.List[typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]]
BboxType = typing.Tuple[float, float, float, float]

class LTWrapper:
  elem: pdfminer.layout.LTComponent
  parent_idx: typing.Union[int, None]
  def __init__(
    self,
    elem: pdfminer.layout.LTComponent,
    parent_idx: typing.Union[int, None]
  ) -> None:
    self.elem = elem
    self.parent_idx = parent_idx

  def __dict__(self):
    original_path = []
    text = ""
    if isinstance(self.elem, pdfminer.layout.LTCurve):
      original_path = self.elem.original_path
    if isinstance(self.elem, pdfminer.layout.LTText):
      text = self.elem.get_text()

    return {
      "elem": {
        "x0": self.elem.x0,
        "y0": self.elem.y0,
        "width": self.elem.width,
        "height": self.elem.height,
        "bbox": self.elem.bbox,
        "original_path": original_path,
        "text": text,
      },
      "parent_idx": self.parent_idx
    }

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

def get_underlying(elems: typing.Iterable[pdfminer.layout.LTComponent]) -> ElemListType:
  out: ElemListType = []
  for elem in elems:
    extend_out_if_element(out=out, elem=get_underlying_from_element(elem=elem))
  return out

def get_underlying_parent_links_impl(
  out: typing.List[LTWrapper],
  elem: pdfminer.layout.LTComponent,
  elem_parent_idx: typing.Union[None, int]
):
  if isinstance(elem, pdfminer.layout.LTContainer):
    out.append(LTWrapper(elem=elem, parent_idx=elem_parent_idx)) # Add the container
    child_parent_idx = len(out) - 1 # Get the container's idx
    for child in elem:
      # Add the first child
      # Get the first child's idx
      # Add the first child's children - recurse
      get_underlying_parent_links_impl(out=out, elem=child, elem_parent_idx=child_parent_idx)
  elif isinstance(elem, pdfminer.layout.LTChar):
    if elem_parent_idx is None:
      print(elem, elem_parent_idx)
    out.append(LTWrapper(elem, parent_idx=elem_parent_idx))
  elif isinstance(elem, pdfminer.layout.LTAnno):
    text = elem.get_text()
    if text != "\n" and text != " ":
      print("Unhandled LTAnno", elem)
    # Not Added
  elif isinstance(elem, pdfminer.layout.LTCurve):
    out.append(LTWrapper(elem, parent_idx=elem_parent_idx))
  elif isinstance(elem, pdfminer.layout.LTFigure):
    # Not Added
    pass
  else:
    print("Unhandled elem:", elem)

def get_underlying_parent_links(
  elems: typing.Iterable[pdfminer.layout.LTComponent],
):
  out: typing.List[LTWrapper] = []
  for elem in elems:
    get_underlying_parent_links_impl(out=out, elem=elem, elem_parent_idx=None)
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
