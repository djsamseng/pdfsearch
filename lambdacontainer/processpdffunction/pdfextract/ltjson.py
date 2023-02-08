
import enum
import json
import typing

import pdfminer.layout

from . import debug_utils
from . import path_utils

ElemListType = typing.List[typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]]
BboxType = typing.Tuple[float, float, float, float]

class LTJson:
  def __init__(
    self,
    elem: typing.Union[pdfminer.layout.LTComponent, None] = None,
    parent_idx: typing.Union[int, None] = None,
    children_idxes: typing.List[int] = [],
    serialized_json: typing.Union[typing.Dict[str, typing.Any], None] = None,
  ) -> None:
    # Public serialized
    self.bbox: typing.Tuple[float, float, float, float] = (0, 0, 0, 0)
    self.width: float = 0
    self.height: float = 0
    self.label: typing.Union[str, None] = None # text of elements inside
    self.text: typing.Union[str, None] = None # get_text()
    self.size = None
    self.original_path = None
    self.linewidth = None
    self.is_container = False
    self.is_annotation = False
    self.is_line = False
    self.is_rect = False
    self.parent_idx = None
    self.children_idxes = []

    # Prive unserialized
    self.__path_lines = None
    self.__zeroed_path_lines: typing.Union[typing.List[path_utils.LinePointsType], None] = None
    self.__zeroed_bbox: typing.Union[BboxType, None] = None

    if elem is not None:
      self.bbox = elem.bbox
      self.width = elem.width
      self.height = elem.height
      self.parent_idx = parent_idx
      self.children_idxes = children_idxes
      if isinstance(elem, pdfminer.layout.LTCurve):
        if isinstance(elem, pdfminer.layout.LTRect):
          self.is_rect = True
        if isinstance(elem, pdfminer.layout.LTLine):
          self.is_line = True
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
      self.bbox = serialized_json["bbox"]
      if "width" in serialized_json:
        self.width = serialized_json["width"]
      if "height" in serialized_json:
        self.height = serialized_json["height"]
      if "label" in serialized_json:
        self.label = serialized_json["label"]
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
      if "is_line" in serialized_json:
        self.is_line = serialized_json["is_line"]
      if "is_rect" in serialized_json:
        self.is_rect = serialized_json["is_rect"]
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

  def __hash__(self) -> int:
    return hash(self.__str__())

  def __repr__(self) -> str:
    return self.__str__()

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
    self.__zeroed_path_lines = path_utils.get_zeroed_path_lines(path_lines=path_lines)
    return self.__zeroed_path_lines

  def get_zeroed_bbox(self):
    if self.__zeroed_bbox is not None:
      return self.__zeroed_bbox
    x0, y0, x1, y1 = self.bbox
    minx = min(x0, x1)
    miny = min(y0, y1)
    self.__zeroed_bbox = (x0-minx, y0-miny, x1-minx, y1-miny)
    return self.__zeroed_bbox

  def as_dict(self):
    out: typing.Dict[str, typing.Any] = dict()
    for key in self.__dict__.keys():
      if not key.startswith("_{0}__".format(self.__class__.__name__)):
        out[key] = self.__dict__[key]
    return out

class LTJsonEncoder(json.JSONEncoder):
  def default(self, o: typing.Any):
    if isinstance(o, LTJson):
      return o.as_dict()
    return None


class ScheduleTypes(str, enum.Enum):
  DOORS = "doors"
  WINDOWS = "windows"
  LIGHTING = "lighting"
class PdfRowPtr(typing.TypedDict):
  schedule: ScheduleTypes
  page: int
  row: int
class PdfScheduleCell(typing.TypedDict):
  key: str
  label: str
  bbox: BboxType
  rowPtr: PdfRowPtr
class PdfElem(typing.TypedDict):
  label: str
  bbox: BboxType
  rowPtr: PdfRowPtr
class PdfScheduleRow(typing.TypedDict):
  elems: typing.List[PdfElem]
  cells: typing.List[PdfScheduleCell]
class PdfSchedule(typing.TypedDict):
  headerRow: PdfScheduleRow
  rows: typing.List[PdfScheduleRow]

class PdfSummaryJson(typing.TypedDict):
  doors: typing.Dict[int, PdfSchedule]
  windows: typing.Dict[int, PdfSchedule]
  lighting: typing.Dict[int, PdfSchedule]
  houseName: str
  architectName: str
  pageNames: typing.Dict[int, str]
