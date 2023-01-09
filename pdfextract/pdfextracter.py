
import json
import typing

import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils

import debug_utils
import path_utils

ElemListType = typing.List[typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]]
BboxType = typing.Tuple[float, float, float, float]

class LTJsonEncoder(json.JSONEncoder):
  def default(self, o: typing.Any):
    if isinstance(o, LTJson):
      return o.as_dict()

class LTJson:
  def __init__(
    self,
    elem: typing.Union[pdfminer.layout.LTComponent, None] = None,
    parent_idx: typing.Union[int, None] = None,
    children_idxes: typing.List[int] = [],
    serialized_json: typing.Union[typing.Dict[str, typing.Any], None] = None,
  ) -> None:
    # Public serialized
    self.bbox = (0, 0, 0, 0)
    self.width = 0
    self.height = 0
    self.text = None
    self.size = None
    self.original_path = None
    self.linewidth = None
    self.is_container = False
    self.is_annotation = False
    self.parent_idx = None
    self.children_idxes = []

    # Prive unserialized
    self.__path_lines = None
    self.__zeroed_path_lines: typing.Union[typing.List[path_utils.LinePointsType], None] = None

    if elem is not None:
      self.bbox = elem.bbox
      self.width = elem.width
      self.height = elem.height
      self.parent_idx = parent_idx
      self.children_idxes = children_idxes
      if isinstance(elem, pdfminer.layout.LTCurve):
        self.original_path = elem.original_path
        self.linewidth = elem.linewidth
      if isinstance(elem, pdfminer.layout.LTText):
        self.text = elem.get_text()
        if isinstance(elem, pdfminer.layout.LTChar):
          self.size = elem.size
      if isinstance(elem, pdfminer.layout.LTContainer):
        self.is_container = True
      if isinstance(elem, pdfminer.layout.LTAnno):
        self.is_annotation = True

    if serialized_json is not None:
      if "bbox" in serialized_json:
        self.bbox = serialized_json["bbox"]
      if "width" in serialized_json:
        self.width = serialized_json["width"]
      if "height" in serialized_json:
        self.height = serialized_json["height"]
      if "text" in serialized_json:
        self.text = serialized_json["text"]
      if "size" in serialized_json:
        self.size = serialized_json["size"]
      if "original_path" in serialized_json:
        self.original_path = serialized_json["original_path"]
      if "linewidth" in serialized_json:
        self.linewidth = serialized_json["linewidth"]
      if "is_container" in serialized_json:
        self.is_container = serialized_json["is_container"]
      if "is_annotation" in serialized_json:
        self.is_annotation = serialized_json["is_annotation"]
      if "parent_idx" in serialized_json:
        self.parent_idx = serialized_json["parent_idx"]
      if "children_idxes" in serialized_json:
        self.children_idxes = serialized_json["children_idxes"]

  def __eq__(self, other: object) -> bool:
    if not debug_utils.is_debug:
      print("===== __eq__ should not be called in production =====")
      return False
    if not isinstance(other, LTJson):
      return False
    for key in self.__dict__.keys():
      if key == "bbox":
        if not self.__eq_bbox(other):
          return False
      elif key == "original_path":
        if not self.__eq_original_path(other):
          return False
      elif self.__dict__[key] != other.__dict__[key]:
        print("Failed:", key, self.__dict__[key], other.__dict__[key])
        return False
    return True

  def __eq_bbox(self, other: object) -> bool:
    if not debug_utils.is_debug:
      print("===== __eq_bbox should not be called in production =====")
      return False
    if not isinstance(other, LTJson):
      return False
    for itr in range(len(self.bbox)):
      if self.bbox[itr] != other.bbox[itr]:
        print("Bbox failed")
        return False
    return True

  def __eq_original_path(self, other: object) -> bool:
    if not debug_utils.is_debug:
      print("===== __eq_original_path should not be called in production =====")
      return False
    if not isinstance(other, LTJson):
      return False
    if self.original_path is None and other.original_path is None:
      return True
    if self.original_path is None or other.original_path is None:
      print("original path failed")
      return False

    self_list = self.__deep_tuple_to_list(self.original_path)
    other_list = self.__deep_tuple_to_list(other.original_path)
    return self_list == other_list

  def __deep_tuple_to_list(self, iterable: typing.Iterable[typing.Any]) -> typing.List[typing.Any]:
    out: typing.List[typing.Any] = []
    for elem in iterable:
      if isinstance(elem, tuple) or isinstance(elem, list):
        out_elem = self.__deep_tuple_to_list(typing.cast(typing.Iterable[typing.Any], elem))
        out.append(out_elem)
      else:
        out.append(elem)
    return out

  def __str__(self) -> str:
    return json.dumps(self.as_dict())

  def get_path_lines(self):
    if self.__path_lines is not None:
      return self.__path_lines

    if self.original_path is not None:
      self.__path_lines = path_utils.path_to_lines(path=self.original_path)
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
    out: typing.Dict[str, typing.Any] = dict()
    for key in self.__dict__.keys():
      if not key.startswith("_{0}__".format(self.__class__.__name__)):
        out[key] = self.__dict__[key]
    return out

def get_underlying_parent_links_impl(
  out: typing.List[LTJson],
  elem: pdfminer.layout.LTComponent,
  elem_parent_idx: typing.Union[None, int]
):
  if isinstance(elem, pdfminer.layout.LTContainer):
    out.append(LTJson(elem=typing.cast(pdfminer.layout.LTComponent, elem), parent_idx=elem_parent_idx)) # Add the container
    child_parent_idx = len(out) - 1 # Get the container's idx
    for child in typing.cast(typing.Iterable[pdfminer.layout.LTComponent], elem):
      # Add the first child
      # Get the first child's idx
      # Add the first child's children - recurse
      get_underlying_parent_links_impl(out=out, elem=child, elem_parent_idx=child_parent_idx)
  elif isinstance(elem, pdfminer.layout.LTChar):
    if elem_parent_idx is None:
      print(elem, elem_parent_idx)
    out.append(LTJson(elem, parent_idx=elem_parent_idx))
  elif isinstance(elem, pdfminer.layout.LTAnno):
    text = elem.get_text()
    if text != "\n" and text != " ":
      print("Unhandled LTAnno", elem)
    # Not Added
  elif isinstance(elem, pdfminer.layout.LTCurve):
    out.append(LTJson(elem, parent_idx=elem_parent_idx))
  elif isinstance(elem, pdfminer.layout.LTFigure):
    # Not Added
    print("Unhandled figure", elem)
    pass
  else:
    print("Unhandled elem:", elem)

def get_underlying_parent_links(
  elems: typing.Iterable[pdfminer.layout.LTComponent],
):
  out: typing.List[LTJson] = []
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

def filter_contains_bbox_hierarchical(elems: typing.Iterable[LTJson], bbox: BboxType) -> typing.List[LTJson]:
  out: typing.List[LTJson] = []
  json_encoder = LTJsonEncoder()
  old_idx_to_new_idx: typing.Dict[int, int] = dict()
  for old_idx, wrapper in enumerate(elems):
    new_parent_idx = None
    if wrapper.parent_idx is not None:
      if wrapper.parent_idx in old_idx_to_new_idx:
        new_parent_idx = old_idx_to_new_idx[wrapper.parent_idx]
    if wrapper.is_annotation:
      continue
    if box_contains(outer=bbox, inner=wrapper.bbox):
      elem_copy = LTJson(serialized_json=json.loads(json_encoder.encode(wrapper)))
      elem_copy.parent_idx = new_parent_idx
      out.append(elem_copy)
      old_idx_to_new_idx[old_idx] = len(out) - 1

  return out
