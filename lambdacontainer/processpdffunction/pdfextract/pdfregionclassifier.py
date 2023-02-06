
import collections
import enum
import typing

import rtree

from . import ltjson, pdfelemtransforms

# TODO: Connection strengths
# a toilet symbol highly effects what kind of room it is
# an area being a schedule box highly effects the symbols inside of it
# TODO: PdfRegionSearch
# 1. Rtree subdivide regions
# 2. Lowest level symbols, lines, characters identified
# 3. Merge lower levels to form higher levels (ex: words, sentences, rooms) using connection strengths and merge rules
# 4. Repeat 1. passing down high level votes (ex: a schedule box makes the lighting symbol inside of it no longer an instance)
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
