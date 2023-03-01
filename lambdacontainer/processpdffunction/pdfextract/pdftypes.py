
import abc
import collections
import enum
import json
import math
import re
import typing

import pdfminer.layout, pdfminer.utils
import rtree, rtree.index

from . import path_utils

Bbox = path_utils.Bbox
FLOAT_MIN = 0.001


class ClassificationType(enum.Enum):
  SLOPE = 1
  LENGTH = 2
  TEXT = 3
  LEFT_RIGHT = 4
  SIZE = 5

class LabelType(int, enum.Enum):
  FRACTION = 1
  DISTANCE = 2
  NUMBER = 3
  MEASUREMENT = 4
  WORD = 5
  BEDROOM = 6
  BATHROOM = 7
  ROOM = 8
  FEET = 9
  INCHES = 10
  DECIMAL = 11
  INT = 12
  FRACTION_LINE = 13

class Direction(enum.Enum):
  LEFT = 1
  RIGHT = 2
  UP = 3
  DOWN = 4

decimal_regex_cap = re.compile("^[\\d]*\\.[\\d]+$")
int_regex_cap = re.compile("^\\d+$")
fraction_regex_cap = re.compile("^[\\d]+/[\\d]+$")
measurement_regex_cap = re.compile("\"|'|feet|foot|inches|inch?$", flags=re.IGNORECASE)

def text_has_decimal(s: str):
  match = decimal_regex_cap.finditer(s)
  for m in match:
    return m.span()
  return None

def text_has_measurement(s: str):
  match = measurement_regex_cap.finditer(s)
  for m in match:
    return m.span()
  return None

def text_has_fraction(s: str):
  match = fraction_regex_cap.finditer(s)
  for m in match:
    return m.span()
  return None

def text_has_int(s: str):
  match = int_regex_cap.finditer(s)
  for m in match:
    return m.span()
  return None

def get_numeric_text_labels(
  s: str
) -> typing.List[typing.Tuple[LabelType, float]]:
  out: typing.List[typing.Tuple[LabelType, float]] = []

  decimal_span = text_has_decimal(s)
  fraction_span = text_has_fraction(s)
  int_span = text_has_int(s)
  measurement_span = text_has_measurement(s)

  numeric_span = decimal_span or fraction_span or int_span
  if numeric_span is None and measurement_span is None:
    return []
  measurement_prob = 0.2 if numeric_span is None else 1.

  if measurement_span is not None:
    out.append((LabelType.MEASUREMENT, measurement_prob))
    text = s[measurement_span[0]: measurement_span[1]].lower()
    if text == "feet" or text == "foot" or text == "'":
      out.append((LabelType.FEET, measurement_prob))
    elif text == "inches" or text == "inch" or text == "\"":
      out.append((LabelType.INCHES, measurement_prob))

    if numeric_span is None and measurement_span[0] != 0:
      return []
  if numeric_span is None:
    return out

  out.append((LabelType.NUMBER, 1.))

  if decimal_span is not None:
    out.append((LabelType.DECIMAL, 1.))
  if fraction_span is not None:
    out.append((LabelType.FRACTION, 1.))
    if int_span is not None:
      between = s[int_span[1]:fraction_span[0]]
      if between != " ":
        return []
    elif fraction_span[0] != 0:
      return []
  elif int_span is not None:
    out.append((LabelType.INT, 1.))


  if measurement_span is not None:
    between = s[numeric_span[1]:measurement_span[0]]
  else:
    between = s[numeric_span[1]:]
  if between != "" and between != " ":
    return []

  return out

class Circle():
  def __init__(
    self,
    r1: float,
    r2: float,
  ) -> None:
    self.r1 = r1
    self.r2 = r2

NodeId = int
class ClassificationNode():
  id_itr: NodeId = 0
  def __init__(
    self,
    elem: typing.Union[None, pdfminer.layout.LTComponent],
    bbox: Bbox,
    line: typing.Union[None, path_utils.LinePointsType],
    text: typing.Union[None, str],
    child_ids: typing.List[int],
  ) -> None:
    self.node_id = ClassificationNode.id_itr
    ClassificationNode.id_itr += 1
    self.elem = elem

    self.bbox = bbox
    self.line = line
    self.text = text
    self.labels: typing.DefaultDict[LabelType, float] = collections.defaultdict(float)
    self.child_ids = set(child_ids)

    self.parent_ids: typing.Set[NodeId] = set()
    self.slope = path_utils.line_slope(line=line) if line is not None else 0.
    self.angle = path_utils.line_angle(line=line) if line is not None else 0.
    self.fontsize = 0.
    if isinstance(elem, pdfminer.layout.LTChar):
      self.left_right = elem.upright
    elif abs(self.slope) > 1:
      self.left_right = False
    else:
      self.left_right = True
    if self.left_right:
      self.fontsize = bbox[3] - bbox[1]
    else:
      self.fontsize = bbox[2] - bbox[0]
    self.length = self.__length()

    self.circle: typing.Union[None, Circle] = None

  def width(self):
    return self.bbox[2] - self.bbox[0]

  def height(self):
    return self.bbox[3] - self.bbox[1]

  def activation(
    self,
    other: "ClassificationNode"
  ) -> typing.List[typing.Tuple[ClassificationType, float]]:
    if self.line is not None and other.line is not None:
      slope_activation = abs(self.slope - other.slope) / path_utils.MAX_SLOPE
      length_activation = abs(self.length - other.length) / max(self.length, other.length)
      return [
        (ClassificationType.SLOPE, slope_activation),
        (ClassificationType.LENGTH, length_activation),
      ]
    elif self.text is not None and other.text is not None:
      text_activation = 1. if self.text == other.text else 0. # TODO: mincut distance
      upright_activation = 1. if self.left_right == other.left_right else 0.
      size_activation = abs(self.width() - other.width()) + abs(self.height() - other.height())
      if size_activation < 0.001:
        size_activation = 1
      else:
        size_activation = min(1, 1 / size_activation)
      return [
        (ClassificationType.TEXT, text_activation),
        (ClassificationType.LEFT_RIGHT, upright_activation),
        (ClassificationType.SIZE, size_activation),
      ]
    return []

  def get_classifications(self) -> typing.List[typing.Tuple[ClassificationType, typing.Any]]:
    if self.line is not None:
      return [
        (ClassificationType.SLOPE, self.slope),
        (ClassificationType.LENGTH, self.length),
      ]
    elif self.text is not None:
      return [
        (ClassificationType.TEXT, self.text),
        (ClassificationType.LEFT_RIGHT, self.left_right),
        (ClassificationType.SIZE, self.width() if self.left_right else self.height()),
      ]
    return []

  def labelize(self):
    if len(self.labels) > 0:
      return
    if self.text is not None:
      text_labels = get_numeric_text_labels(s=self.text)
      for label, prob in text_labels:
        self.labels[label] = prob
    if self.line is not None:
      if 0 <= self.slope and self.slope < 3:
        self.labels[LabelType.FRACTION_LINE] = 0.1
    if self.text is not None:
      if self.text == "/":
        self.labels[LabelType.FRACTION_LINE] = 0.1

  def __length(self):
    if self.line is not None:
      return path_utils.line_length(line=self.line)
    elif self.text is not None:
      if self.left_right:
        return self.bbox[2] - self.bbox[0]
      else:
        return self.bbox[3] - self.bbox[1]
    else:
      return 0.

  def __repr__(self) -> str:
    return self.__str__()

  def __str__(self) -> str:
    return json.dumps(self.as_dict())

  def as_dict(self):
    out: typing.Dict[str, typing.Any] = dict()
    for key in self.__dict__.keys():
      if key == "elem":
        continue
      elif key == "parent_ids" or key == "child_ids":
        out[key] = list(self.__dict__[key])
      elif not key.startswith("_{0}__".format(self.__class__.__name__)):
        out[key] = self.__dict__[key]
    return out

class BaseSymbol(metaclass=abc.ABCMeta):
  @property
  @abc.abstractmethod
  def width(self) -> float:
    pass

  @property
  @abc.abstractmethod
  def height(self) -> float:
    pass

  @abc.abstractmethod
  def activation(
    self,
    node: ClassificationNode,
    weights: typing.Dict[ClassificationType, float],
  ) -> float:
    pass

class TextSymbol(BaseSymbol):
  def __init__(
    self,
    width: float,
    height: float,
    text: str
  ):
    self.__width = width
    self.__height = height
    self.text = text

  @property
  def width(self):
    return self.__width

  @property
  def height(self):
    return self.__height

  def activation(
    self,
    node: ClassificationNode,
    weights: typing.Dict[ClassificationType, float],
  ):
    text_activation = 1. if self.text == node.text else 0. # TODO: mincut distance
    size_activation = 1 - math.tanh(
      abs(self.width - node.width()) + abs(self.height - node.height())
    )
    text_weight = weights[ClassificationType.TEXT] if ClassificationType.TEXT in weights else 0.
    size_weight = weights[ClassificationType.SIZE] if ClassificationType.SIZE in weights else 0.
    divisor = text_weight + size_weight
    if divisor < FLOAT_MIN:
      divisor = 1.
    weighted_activation = text_activation * text_weight + size_activation * size_weight
    return weighted_activation / divisor

class LineSymbol(BaseSymbol):
  def __init__(
    self,
    line: path_utils.LinePointsType
  ) -> None:
    bounding_box = path_utils.lines_bounding_bbox(elems=[line])
    self.__line = line
    self.__zero_line = path_utils.zero_line(line=line, bounding_box=bounding_box)
    self.__width = bounding_box[2] - bounding_box[0]
    self.__height = bounding_box[3] - bounding_box[1]
    self.__slope = path_utils.line_slope(line=self.__zero_line)
    self.__length = path_utils.line_length(line=self.__zero_line)

  @property
  def width(self):
    return self.__width

  @property
  def height(self):
    return self.__height

  @property
  def line(self):
    return self.__line

  @property
  def slope(self):
    return self.__slope

  @property
  def length(self):
    return self.__length

  def activation(
    self,
    node: ClassificationNode,
    weights: typing.Dict[ClassificationType, float],
  ):
    slope_activation = 1 - math.tanh(abs(self.__slope - node.slope))

    length_activation = 1 - math.tanh(
      abs(self.__length - node.length) / max(self.__length, node.length, FLOAT_MIN)
    )
    return min(slope_activation, length_activation)

  def __repr__(self) -> str:
    return self.__str__()

  def __str__(self) -> str:
    return json.dumps(self.as_dict())

  def as_dict(self):
    out: typing.Dict[str, typing.Any] = dict()
    split_token = "_{0}__".format(self.__class__.__name__)
    for key in self.__dict__.keys():
      if key.startswith(split_token):
        str_key = key.split(split_token)[1]
        out[str_key] = self.__dict__[key]
      else:
        out[key] = self.__dict__[key]
    return out

class ConnectionType(enum.Enum):
  POSITION = 1
  MEANING = 2

class Connection():
  def __init__(
    self,
    type: ConnectionType,
    strength: float) -> None:
    self.type = type
    self.strength = strength

class MSymbol():
  def __init__(
    self,
    value: typing.Any,
    desc: typing.Union[None, str] = None,
  ) -> None:
    self.value = value
    self.desc = desc or str(value)
    self.connections: typing.DefaultDict[
      ConnectionType,
      typing.List[Connection]
    ] = collections.defaultdict(list)

def make_symbols():
  symbols = [ # type: ignore
    MSymbol(value="mahogony"),
    MSymbol(value="mahog"), # should be learned
    MSymbol(value='"'),
    MSymbol(value="quotation mark"),
    MSymbol(value="feet"),
    MSymbol(value="inches"),
    MSymbol(value="plural"),
  ]


class BaseMatcher(metaclass=abc.ABCMeta):
  pass

class ShapeMatcher(BaseMatcher):
  def __init__(
    self,
    shape_id: str,
    lines: typing.List[path_utils.LinePointsType],
  ) -> None:
    self.shape_id = shape_id
    self.lines = lines

class ApproximateShapeMatcher(BaseMatcher):
  def __init__(
    self
  ) -> None:
    pass

class OffsetMatcher():
  def __init__(self) -> None:
    pass

class TextMatcher(BaseMatcher):
  def __init__(
    self,
    text_id: str,
    regex: str
  ) -> None:
    self.text_id = text_id
    self.regex = re.compile(regex)

class LookForElem():
  def __init__(
    self,
    text: typing.Union[None, TextMatcher],
    shape: typing.Union[None, ShapeMatcher, ApproximateShapeMatcher],
    children: typing.List[
      typing.Tuple["LookForElem", OffsetMatcher]
    ],
  ):
    pass

def make_word_matcher():
  # 1 1/3"
  # given an x,y is there a char here?
  # If so grab it, assign its parent to me and continue
  # If it doesn't pan out, destroy parent links
  pass

def make_table_matcher():
  # Do we have rows and columns?
  pass

def make_window_schedule_matcher():

  # We might have a surrounding box we might now
  # During search we find the leafs and they activate upward
  # Certain things can be missing, we can still try to make the jump
  # If we make the jump and it turns out to be correct, add a new connection
  matcher = LookForElem(
    text=TextMatcher(text_id="window schedule key", regex="^window$"),
    shape=None,
    children=[],
  )
  return matcher

class MatcherManager():
  def __init__(self) -> None:
    self.searches: typing.List[LookForElem] =  [
      make_window_schedule_matcher()
    ]

Boundaries = typing.List[
  typing.Union[
    None,
    typing.Tuple[
      float, # the boundary
      typing.Union[None, ClassificationNode] # Why
    ],
  ]
]
