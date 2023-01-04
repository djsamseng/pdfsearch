

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

def filter_contains_bbox_hierarchical(elems: typing.Iterable[LTWrapper], bbox: BboxType) -> typing.List[LTWrapper]:
  out = []
  to_process: typing.List[LTWrapper] = []
  old_idx_to_new_idx = dict()
  for old_idx, wrapper in enumerate(elems):
    elem = wrapper.elem
    new_parent_idx = None
    if wrapper.parent_idx is not None:
      if wrapper.parent_idx in old_idx_to_new_idx:
        new_parent_idx = old_idx_to_new_idx[wrapper.parent_idx]
    if isinstance(elem, pdfminer.layout.LTAnno):
      continue
    if box_contains(outer=bbox, inner=elem.bbox):
      out.append(LTWrapper(elem=elem, parent_idx=new_parent_idx))
      old_idx_to_new_idx[old_idx] = len(out) - 1
    elif isinstance(elem, pdfminer.layout.LTContainer):
      # I don't fit so I won't be included in out but my children might
      to_process.append(wrapper)

  while len(to_process) > 0:
    container_wrapper = to_process.pop()
    container_elem = container_wrapper.elem
    for wrapper in container_elem:
      elem = wrapper.elem
      new_parent_idx = None
      if wrapper.parent_idx is not None:
        if wrapper.parent_idx in old_idx_to_new_idx:
          new_parent_idx = old_idx_to_new_idx[wrapper.parent_idx]
      if isinstance(elem, pdfminer.layout.LTAnno):
        continue
      if box_contains(outer=bbox, inner=elem.bbox):
        out.append(LTWrapper(elem=elem, parent_idx=new_parent_idx))
        old_idx_to_new_idx[old_idx] = len(out) - 1
      elif isinstance(elem, pdfminer.layout.LTContainer):
        # I don't fit so I won't be included in out but my children might
        to_process.append(elem)

  return out
