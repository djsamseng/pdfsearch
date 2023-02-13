
import json
import typing

import pdfminer.layout, pdfminer.utils

from . import path_utils

Bbox = typing.Tuple[float, float, float, float]

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

  def width(self):
    return self.bbox[2] - self.bbox[0]

  def height(self):
    return self.bbox[3] - self.bbox[1]

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
