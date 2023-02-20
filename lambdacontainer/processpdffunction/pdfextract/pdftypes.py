
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
  UPRIGHT = 4
  SIZE = 5

class LabelType(enum.Enum):
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

decimal_regex_cap = re.compile("^[\\d]*\\.[\\d]+")
int_regex_cap = re.compile("^\\d+")
fraction_regex_cap = re.compile("[\\d]+/[\\d]+")
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
    if isinstance(elem, pdfminer.layout.LTChar):
      self.upright = elem.upright
    else:
      self.upright = True
    self.bbox = bbox
    self.line = line
    self.text = text
    self.labels: typing.DefaultDict[LabelType, float] = collections.defaultdict(float)
    self.child_ids = set(child_ids)

    self.parent_ids: typing.Set[NodeId] = set()
    self.slope = path_utils.line_slope(line=line) if line is not None else 0.
    self.length = self.__length()

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
      upright_activation = 1. if self.upright == other.upright else 0.
      size_activation = abs(self.width() - other.width()) + abs(self.height() - other.height())
      if size_activation < 0.001:
        size_activation = 1
      else:
        size_activation = min(1, 1 / size_activation)
      return [
        (ClassificationType.TEXT, text_activation),
        (ClassificationType.UPRIGHT, upright_activation),
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
        (ClassificationType.UPRIGHT, self.upright),
        (ClassificationType.SIZE, self.width() if self.upright else self.height()),
      ]
    return []

  def labelize(self):
    if len(self.labels) > 0:
      return
    if self.text is not None:
      text_labels = get_numeric_text_labels(s=self.text)
      for label, prob in text_labels:
        self.labels[label] = prob

  def __length(self):
    if self.line is not None:
      return path_utils.line_length(line=self.line)
    elif self.text is not None:
      if self.upright:
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



class NodeManager():
  def __init__(
    self,
    layers: typing.List[typing.List[ClassificationNode]],
  ) -> None:
    self.layers: typing.DefaultDict[
      int,
      typing.Set[NodeId]
    ] = collections.defaultdict(set)
    self.nodes: typing.Dict[NodeId, ClassificationNode] = {}

    self.indexes: typing.Dict[
      int,
      rtree.index.Index
    ] = {}
    for idx, layer in enumerate(layers):
      self.create_layer(layer_idx=idx)
      for node in layer:
        self.layers[idx].add(node.node_id)
        self.nodes[node.node_id] = node
      self.index_layer(layer_idx=idx)

  def create_layer(self, layer_idx: int):
    if layer_idx in self.layers:
      print("=== Warning: Destroying existing layer {0} ===".format(layer_idx))
    self.layers[layer_idx] = set()

  def add_node(
    self,
    elem: typing.Union[None, pdfminer.layout.LTComponent],
    bbox: Bbox,
    line: typing.Union[None, path_utils.LinePointsType],
    text: typing.Union[None, str],
    child_ids: typing.List[int],
    layer_idx: int,
  ):
    if layer_idx not in self.layers:
      self.create_layer(layer_idx=layer_idx)
    node = ClassificationNode(
      elem=elem,
      bbox=bbox,
      line=line,
      text=text,
      child_ids=child_ids,
    )
    self.layers[layer_idx].add(node.node_id)
    self.nodes[node.node_id] = node
    if layer_idx in self.indexes:
      self.indexes[layer_idx].add(id=node.node_id, coordinates=node.bbox, obj=None)
    return node

  def index_layer(self, layer_idx: int):
    if layer_idx in self.indexes:
      print("=== Warning: Destroying existing index {0} ===".format(layer_idx))
    def insertion_generator(nodes: typing.List[ClassificationNode]):
      for node in nodes:
        yield (node.node_id, node.bbox, None)
    layer_nodes = [self.nodes[node_id] for node_id in self.layers[layer_idx]]
    index = rtree.index.Index(insertion_generator(nodes=layer_nodes))
    self.indexes[layer_idx] = index

  def intersection(self, layer_idx: int, bbox: Bbox):
    node_ids = self.indexes[layer_idx].intersection(coordinates=bbox, objects=False)
    return [ self.nodes[node_id] for node_id in node_ids ]

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
  symbols = [
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
