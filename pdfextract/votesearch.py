
from abc import ABCMeta, abstractmethod
import collections
import re
import typing

import rtree

from . import pdfindexer
from .ltjson import LTJson, LTJsonResponse

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

def item_is_multiline_text(item: LTJsonResponse):
  if item.label is not None:
    item_newline = item.label.find("\n")
    item_multiline = item_newline >= 0 and \
      item_newline - 1 < len(item.label)
    return item_multiline
  return False

def remove_duplicate_bbox(items: typing.List[LTJsonResponse]):
  bbox_indexer = rtree.index.Index()
  idx = 0
  radius = 0
  out: typing.List[LTJsonResponse] = []
  should_swap_out: typing.List[bool] = []
  for item in items:
    results = bbox_indexer.intersection(item.bbox)
    if results is not None:
      results = list(results)
    if results is not None and len(results) == 1:
      idx = results[0]
      if should_swap_out[idx]:
        out[idx] = item
    if results is None or len(list(results)) == 0:
      x0, y0, x1, y1 = item.bbox
      bbox = (x0-radius, y0-radius, x1+radius, y1+radius)
      bbox_indexer.insert(idx, bbox)
      out.append(item)
      should_swap_out.append(item_is_multiline_text(item=item))
  return out

class SearchRule(metaclass=ABCMeta):
  @abstractmethod
  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    pass

  @abstractmethod
  def get_results(self) -> typing.Dict[str, typing.Any]:
    pass

MultiClassSearchRuleResults = typing.DefaultDict[
  str, # class_name
  typing.DefaultDict[
    str, # elem_type
    typing.List[LTJsonResponse]
  ]
]
class MultiClassSearchRule(SearchRule):
  def __init__(self, shape_matches: typing.List[LTJson], description: str, regex: str) -> None:
    '''
    regex extracts the window types. the remaining text is the id
    '''
    self.shape_matches = shape_matches
    self.description = description
    self.regex = re.compile(regex) # (?P<window_class>[a-zA-Z])(?P<window_id>\\d\\d)
    self.results: MultiClassSearchRuleResults = self.__create_results_dict()
    self.radius = max([max(s.width, s.height) for s in shape_matches])

  def __create_results_dict(self) -> MultiClassSearchRuleResults:
    return collections.defaultdict( # class_name
      lambda: collections.defaultdict( # elem_type
        list
      )
    )

  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    if elem.text is None:
      return
    match = self.regex.search(elem.text)
    if match is None:
      return
    groups = match.groupdict()
    class_name = groups["class_name"]
    elem_type = groups["elem_type"]
    around_bbox = (
      elem.bbox[0] - self.radius,
      elem.bbox[1] - self.radius,
      elem.bbox[2] + self.radius,
      elem.bbox[3] + self.radius,
    )
    # 1.6s
    around_elems = indexer.find_contains(bbox=around_bbox)
    # 2.2s
    for shape in self.shape_matches:
      matching_curves = pdfindexer.find_similar_curves(
        wrapper_to_find=shape,
        wrappers_to_search=around_elems,
        max_dist=2.
      )
      # matching_shape = self.__find_outer_shape(around_elems)
      if len(matching_curves) > 0: #matching_shape is not None:
        matching_shape = LTJsonResponse(elem=matching_curves[0], page_idx=page_number)
        matching_shape.label = elem.text
        print(elem.text, elem.bbox)
        self.results[class_name][elem_type].append(matching_shape)

  def __refine(self):
    for wc in self.results.values():
      for wid_key in wc.keys():
        wc[wid_key] = remove_duplicate_bbox(items=wc[wid_key])

  def get_results(self) -> typing.Dict[str, typing.Any]:
    self.__refine()
    return {
      self.description: self.results
    }

class HouseNameSearchRule(SearchRule):
  def __init__(self) -> None:
    pass

  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    pass

  def get_results(self) -> typing.Dict[str, typing.Any]:
    return {}

class ArchitectNameSearchRule(SearchRule):
  def __init__(self) -> None:
    pass

  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    pass

  def get_results(self) -> typing.Dict[str, typing.Any]:
    return {}

class PageNameSearchRule(SearchRule):
  def __init__(self) -> None:
    pass

  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    pass

  def get_results(self) -> typing.Dict[str, typing.Any]:
    return {}

class VoteSearcher:
  def __init__(self,
    search_rules: typing.List[SearchRule],
  ) -> None:
    self.search_rules = search_rules
    self.votes: typing.Dict[str, typing.Any] = {
      "by_page_number": collections.defaultdict(dict),
      # house names found and probability -> sort by probability
      "house_names": collections.defaultdict(dict),
      "architect_names": collections.defaultdict(dict),
    }

  def process(
    self,
    page_number:int,
    elems: typing.List[LTJson],
    indexer: pdfindexer.PdfIndexer
  ) -> None:
    for elem in elems:
      for rule in self.search_rules:
        rule.process_elem(elem=elem, page_number=page_number, indexer=indexer)

  def refine(self) -> None:
    return

  def get_results(self):
    results: typing.Dict[str, typing.Any] = {}
    for rule in self.search_rules:
      rule_results = rule.get_results()
      merge(dest=results, other=rule_results)
    return results
