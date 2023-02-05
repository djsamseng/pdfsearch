
import collections
import enum
import typing

import rtree

from . import ltjson, pdfelemtransforms

class PdfRegion(enum.Enum):
  SCHEDULE = 1
  FLOOR_PLAN = 2

class PdfRegionClassifier():
  def __init__(self) -> None:
    self.box_classifier = rtree.index.Index()
    self.data: typing.List[typing.Tuple[PdfRegion, float,]] = []

  def classify_region(
    self,
    bbox: ltjson.BboxType,
    region: PdfRegion,
    score: float
  ) -> None:
    idx = len(self.data)
    self.box_classifier.insert(idx, bbox)
    self.data.append((region, score))

  def get_classification(
    self,
    bbox: ltjson.BboxType,
  ) -> typing.DefaultDict[PdfRegion, float]:
    out: typing.DefaultDict[PdfRegion, float] = collections.defaultdict(float)
    matches = self.box_classifier.intersection(bbox, objects=True)
    if matches is None:
      return out
    for item in list(matches):
      region, score = self.data[typing.cast(int, item.id)]
      out[region] += score * pdfelemtransforms.bbox_intersection_area(
        a=bbox,
        b=typing.cast(ltjson.BboxType, item.bbox)
      )
    return out
