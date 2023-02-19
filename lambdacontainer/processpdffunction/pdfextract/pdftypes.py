
import abc
import enum
import json
import math
import re
import typing

import pdfminer.layout, pdfminer.utils

from . import path_utils

Bbox = path_utils.Bbox
FLOAT_MIN = 0.001

class ClassificationType(enum.Enum):
  SLOPE = 1
  LENGTH = 2
  TEXT = 3
  UPRIGHT = 4
  SIZE = 5

class ClassificationNode():
  def __init__(
    self,
    layer_idx: int,
    in_layer_idx: int,
    elem: typing.Union[None, pdfminer.layout.LTComponent],
    bbox: Bbox,
    line: typing.Union[None, path_utils.LinePointsType],
    text: typing.Union[None, str],
    child_idxes: typing.List[int],
  ) -> None:
    self.layer_idx = layer_idx
    self.in_layer_idx = in_layer_idx
    self.elem = elem
    if isinstance(elem, pdfminer.layout.LTChar):
      self.upright = elem.upright
    else:
      self.upright = True
    self.bbox = bbox
    self.line = line
    self.text = text
    self.child_idxes = child_idxes

    self.parent_idxes: typing.List[int] = []
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
      if not key.startswith("_{0}__".format(self.__class__.__name__)):
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
