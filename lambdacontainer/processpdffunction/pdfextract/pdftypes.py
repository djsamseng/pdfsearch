
import enum
import json
import math
import typing

import pdfminer.layout, pdfminer.utils

from . import path_utils

Bbox = typing.Tuple[float, float, float, float]
MAX_SLOPE = 1000.

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
    self.slope = self.__slope()
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
      slope_activation = abs(self.slope - other.slope) / MAX_SLOPE
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

  def __slope(self):
    if self.line is not None:
      (x0, y0), (x1, y1) = self.line
      rise = max(y0, y1) - min(y0, y1)
      run = max(x0, x1) - min(x0, x1)
      x_dir = x1 >= x0
      y_dir = y1 >= y1
      slope_dir = 1. if x_dir == y_dir else -1
      if run < 1 / MAX_SLOPE:
        slope_mag = MAX_SLOPE
      else:
        slope_mag =  min(MAX_SLOPE, rise/run)
      return slope_dir * slope_mag
    return 0.

  def __length(self):
    if self.line is not None:
      (x0, y0), (x1, y1) = self.line
      return math.sqrt((y1-y0) ** 2 + (x1-x0) ** 2)
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
