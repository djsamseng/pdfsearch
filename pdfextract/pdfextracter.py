

import typing

import pdfminer, pdfminer.layout, pdfminer.high_level
import path_utils

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
    self.__path_lines = None
    self.__zeroed_path_lines: typing.Union[typing.List[path_utils.LinePointsType], None] = None

  def get_path_lines(self):
    if self.__path_lines is not None:
      return self.__path_lines

    if isinstance(self.elem, pdfminer.layout.LTCurve):
      if self.elem.original_path is not None:
        self.__path_lines = path_utils.path_to_lines(path=self.elem.original_path)
    if self.__path_lines is None:
      self.__path_lines = []

    return self.__path_lines

  def get_zeroed_path_lines(self):
    if self.__zeroed_path_lines is not None:
      return self.__zeroed_path_lines

    self.__zeroed_path_lines = []
    path_lines = self.get_path_lines()
    if len(path_lines) == 0:
      return self.__zeroed_path_lines

    (x0, y0), (x1, y1) = path_lines[0]
    xmin = min(x0, x1)
    ymin = min(y0, y1)
    for (x0, y0), (x1, y1) in path_lines:
      xmin = min(xmin, min(x0, x1))
      ymin = min(ymin, min(y0, y1))
    for (x0, y0), (x1, y1) in path_lines:
      self.__zeroed_path_lines.append(((x0-xmin, y0-ymin), (x1-xmin, y1-ymin)))
    return self.__zeroed_path_lines

  def as_dict(self):
    original_path = []
    text = ""
    if isinstance(self.elem, pdfminer.layout.LTCurve):
      original_path = self.elem.original_path
    if isinstance(self.elem, pdfminer.layout.LTText):
      text = self.elem.get_text()

    return dict({
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
    })

def get_underlying_parent_links_impl(
  out: typing.List[LTWrapper],
  elem: pdfminer.layout.LTComponent,
  elem_parent_idx: typing.Union[None, int]
):
  if isinstance(elem, pdfminer.layout.LTContainer):
    out.append(LTWrapper(elem=typing.cast(pdfminer.layout.LTComponent, elem), parent_idx=elem_parent_idx)) # Add the container
    child_parent_idx = len(out) - 1 # Get the container's idx
    for child in typing.cast(typing.Iterable[pdfminer.layout.LTComponent], elem):
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
  out: typing.List[LTWrapper] = []
  old_idx_to_new_idx: typing.Dict[int, int] = dict()
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

  return out
