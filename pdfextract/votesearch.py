
from abc import ABCMeta, abstractmethod
import collections
import re
import typing

import rtree

from . import pdfindexer
from .ltjson import LTJson

MergeDict = typing.Dict[str, typing.Any]
def merge(
  dest: MergeDict,
  other: MergeDict
):
  for key, val in other.items():
    if isinstance(val, (dict, collections.defaultdict)):
      node = dest.setdefault(key, {})
      merge(dest=node, other=typing.cast(MergeDict, val))
    else:
      dest[key] = val

def remove_duplicate_bbox(items: typing.List[LTJson]):
  bbox_indexer = rtree.index.Index()
  idx = 0
  radius = 0
  out: typing.List[LTJson] = []
  for item in items:
    results = bbox_indexer.intersection(item.bbox)
    if results is None or len(list(results)) == 0:
      x0, y0, x1, y1 = item.bbox
      bbox = (x0-radius, y0-radius, x1+radius, y1+radius)
      bbox_indexer.insert(idx, bbox)
      out.append(item)
  return out

class SearchRule(metaclass=ABCMeta):
  @abstractmethod
  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    pass

  @abstractmethod
  def get_results(self) -> typing.Dict[str, typing.Any]:
    pass

MultiWindowSearchRuleResults = typing.DefaultDict[
  str, # page_number
  typing.DefaultDict[
    str, # window_class
    typing.DefaultDict[
      str, # window_id
      typing.List[LTJson]
    ]
  ]
]
class MultiWindowSearchRule(SearchRule):
  def __init__(self, shape_matches: typing.List[LTJson], description: str, regex: str) -> None:
    '''
    regex extracts the window types. the remaining text is the id
    '''
    self.shape_matches = shape_matches
    self.description = description
    self.regex = re.compile(regex) # (?P<window_class>[a-zA-Z])(?P<window_id>\\d\\d)
    self.results: MultiWindowSearchRuleResults = collections.defaultdict( # page_number
      lambda: collections.defaultdict( # window_class
        lambda: collections.defaultdict( # window_id
          list
        )
      )
    )
    self.radius = max([max(s.width, s.height) for s in shape_matches])

  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    if elem.text is None:
      return
    match = self.regex.search(elem.text)
    if match is None:
      return
    groups = match.groupdict()
    window_class = groups["window_class"]
    window_id = groups["window_id"]
    around_bbox = (
      elem.bbox[0] - self.radius,
      elem.bbox[1] - self.radius,
      elem.bbox[2] + self.radius,
      elem.bbox[3] + self.radius,
    )
    around_elems = indexer.find_contains(bbox=around_bbox)
    matching_shape = self.__find_outer_shape(around_elems)
    if matching_shape is not None:
      #matching_shape.text = elem.text
      matching_shape = LTJson(serialized_json=matching_shape.as_dict())
      matching_shape.text = elem.text
      self.results[str(page_number)][window_class][window_id].append(matching_shape)

  def __find_outer_shape(self, around_elems: typing.List[LTJson]):
    for shape in self.shape_matches:
      for around_elem in around_elems:
        dw = abs(shape.width - around_elem.width)
        dh = abs(shape.height - around_elem.height)
        # TODO: Match shape instead of size. J01 is matching the wrong shape
        if around_elem.original_path is not None and dw + dh < 10:
          return around_elem
    return None

  def __refine(self):
    for pg in self.results.values():
      for wc in pg.values():
        for wid_key, wid_list in wc.items():
          wc[wid_key] = remove_duplicate_bbox(items=wid_list)

  def get_results(self) -> typing.Dict[str, typing.Any]:
    self.__refine()
    return self.results

class VoteSearcher:
  def __init__(self,
    search_rules: typing.List[SearchRule],
    indexer: pdfindexer.PdfIndexer
  ) -> None:
    self.search_rules = search_rules
    self.indexer = indexer
    self.votes: typing.Dict[str, typing.Any] = {
      "by_page_number": collections.defaultdict(dict),
      # house names found and probability -> sort by probability
      "house_names": collections.defaultdict(dict),
      "architect_names": collections.defaultdict(dict),
    }

  def process(self, page_number:int, elems: typing.List[LTJson]) -> None:
    for elem in elems:
      for rule in self.search_rules:
        rule.process_elem(elem=elem, page_number=page_number, indexer=self.indexer)

  def refine(self) -> None:
    return

  def get_results(self):
    results: typing.Dict[str, typing.Any] = {}
    for rule in self.search_rules:
      rule_results = rule.get_results()
      merge(dest=results, other=rule_results)
    return results
