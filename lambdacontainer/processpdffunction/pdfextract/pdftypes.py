
import abc
import collections
import enum
import json
import math
import typing

import pdfminer.layout, pdfminer.utils

from . import path_utils

Bbox = path_utils.Bbox


class ClassificationType(enum.Enum):
  SLOPE = 1
  LENGTH = 2
  TEXT = 3
  UPRIGHT = 4
  SIZE = 5

class ClassificationNode():
  def __init__(
    self,
    # For linewidth, size upright. Only set on leaf nodes
    elem: typing.Union[None, pdfminer.layout.LTComponent],
    bbox: Bbox,
    line: typing.Union[None, path_utils.LinePointsType],
    text: typing.Union[None, str],
    child_idxes: typing.List[int],
  ) -> None:
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
    node: ClassificationNode
  ) -> typing.List[typing.Tuple[ClassificationType, float]]:
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
    node: ClassificationNode
  ) -> typing.List[typing.Tuple[ClassificationType, float]]:
    text_activation = 1. if self.text == node.text else 0. # TODO: mincut distance
    size_activation = abs(self.width - node.width()) + abs(self.height - node.height())
    if size_activation < 0.001:
      size_activation = 1
    else:
      size_activation = min(1, 1 / size_activation)
    return [
      (ClassificationType.TEXT, text_activation),
      (ClassificationType.SIZE, size_activation),
    ]

class LineSymbol(BaseSymbol):
  def __init__(
    self,
    line: path_utils.LinePointsType
  ) -> None:
    bounding_box = path_utils.lines_bounding_bbox(elems=[line])
    self.__line = path_utils.zero_line(line=line, bounding_box=bounding_box)
    self.__width = bounding_box[2] - bounding_box[0]
    self.__height = bounding_box[3] - bounding_box[1]
    self.__slope = path_utils.line_slope(line=self.__line)
    self.__length = path_utils.line_length(line=self.__line)

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
    node: ClassificationNode
  ) -> typing.List[typing.Tuple[ClassificationType, float]]:
    slope_activation = abs(self.__slope - node.slope) / path_utils.MAX_SLOPE
    length_activation = abs(self.__length - node.length) / max(self.__length, node.length)
    return [
      (ClassificationType.SLOPE, slope_activation),
      (ClassificationType.LENGTH, length_activation),
    ]

class ShapeSymbol(BaseSymbol):
  def __init__(
    self,
    zero_lines: typing.List[path_utils.LinePointsType],
    offsets: typing.List[path_utils.OffsetType]
  ) -> None:
    bounding_box = path_utils.lines_bounding_bbox(elems=zero_lines, offsets=offsets)
    self.__width = bounding_box[2] - bounding_box[0]
    self.__height = bounding_box[3] - bounding_box[1]

  @property
  def width(self):
    return self.__width

  @property
  def height(self):
    return self.__height

  def activation(
    self,
    node: ClassificationNode
  ) -> typing.List[typing.Tuple[ClassificationType, float]]:
    # TODO: Children activate me instead of external activation
    return []
