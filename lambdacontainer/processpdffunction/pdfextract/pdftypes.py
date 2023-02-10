
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
    self.bbox = bbox
    self.line = line
    self.text = text
    self.child_idxes = child_idxes

    self.parent_idxes: typing.List[int] = []
