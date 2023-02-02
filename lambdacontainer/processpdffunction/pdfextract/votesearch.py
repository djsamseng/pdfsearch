
from abc import ABCMeta, abstractmethod
import collections
import re
import typing

import rtree

from . import pdfindexer, pdfextracter
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

def remove_duplicate_bbox_orig(items: typing.List[LTJsonResponse]):
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

def remove_duplicate_bbox(items: typing.List[LTJson]):
  def item_size(item: LTJson):
    x0, y0, x1, y1 = item.bbox
    return (x1-x0) * (y1-y0)
  items.sort(key=lambda x: item_size(x), reverse=True) # pylint:disable=unnecessary-lambda

  bbox_indexer = rtree.index.Index()
  out: typing.List[LTJson] = []
  idx = 0
  radius = 0
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

class PageRecognizerRule(metaclass=ABCMeta):
  @abstractmethod
  def process_page(self, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    pass

  @abstractmethod
  def get_results(self) -> typing.Dict[str, typing.Any]:
    pass

MultiClassSearchRuleResults = typing.DefaultDict[
  int, # page_number
  typing.DefaultDict[
    str, # class_name
    typing.DefaultDict[
      str, # elem_type
      typing.List[LTJsonResponse]
    ]
  ]
]
def create_results_dict() -> MultiClassSearchRuleResults:
  return collections.defaultdict( # page_number
    lambda: collections.defaultdict( # class_name
      lambda: collections.defaultdict( # elem_type
        list
      )
    )
  )
class RegexShapeSearchRule(SearchRule):
  def __init__(self, shape_matches: typing.List[LTJson], description: str, regex: str) -> None:
    '''
    regex extracts the window types. the remaining text is the id
    '''
    self.shape_matches = shape_matches
    self.description = description
    self.regex = re.compile(regex) # (?P<window_class>[a-zA-Z])(?P<window_id>\\d\\d)
    self.results: MultiClassSearchRuleResults = create_results_dict()
    self.radius = max([max(s.width, s.height) for s in shape_matches])
    def default_add_match_to_results(
      results: MultiClassSearchRuleResults,
      page_number: int,
      class_name: str,
      elem_type: str,
      elem: LTJsonResponse
    ):
      results[page_number][class_name][elem_type].append(elem)
    self.add_match_to_results = default_add_match_to_results

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
      if len(matching_curves) > 0:
        matching_shape = LTJsonResponse(elem=matching_curves[0], page_number=page_number)
        matching_shape.label = elem.text
        self.add_match_to_results(
          results=self.results,
          page_number=page_number,
          class_name=class_name,
          elem_type=elem_type,
          elem=matching_shape
        )

  def __refine(self):
    for pg in self.results.values():
      for wc in pg.values():
        for wid_key in wc.keys():
          wc[wid_key] = remove_duplicate_bbox_orig(items=wc[wid_key])

  def get_results(self) -> typing.Dict[str, typing.Any]:
    self.__refine()
    return {
      self.description: self.results
    }

class HouseNameSearchRule(SearchRule):
  def __init__(self, description: str) -> None:
    self.regex = re.compile("^project name.{0,2}")
    self.house_name = ""
    self.description = description

  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    potential_house_name = pdfextracter.extract_house_name(
      regex=self.regex,
      elem=elem,
      indexer=indexer
    )
    if potential_house_name is not None:
      self.house_name = potential_house_name

  def get_results(self) -> typing.Dict[str, typing.Any]:
    return {
      self.description: self.house_name
    }
class ArchitectNameSearchRule(SearchRule):
  def __init__(self, description: str) -> None:
    self.description = description

  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    pass

  def get_results(self) -> typing.Dict[str, typing.Any]:
    return {
      self.description: "Michael Smith"
    }

# TODO: __init__ takes in window_search_rule
# TODO: add to pdfprocessor
class WindowScheduleSearchRule(PageRecognizerRule):
  def __init__(self, window_search_rule: RegexShapeSearchRule) -> None:
    self.window_search_rule = window_search_rule
    self.description = "windowSchedule"
    self.header_row = None
    self.rows = None

  def process_page(self, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    header_row, rows = pdfextracter.extract_table(
      indexer=indexer,
      text_key="window schedule",
      has_header=True,
      header_above_table=False
    )
    if header_row is not None:
      self.header_row = header_row
    if rows is not None:
      self.rows = rows
    def add_match_to_results(
      results: MultiClassSearchRuleResults,
      page_number: int,
      class_name: str,
      elem_type: str,
      elem: LTJsonResponse
    ):
      full_id = class_name + elem_type
      display_class_name = class_name + "##"
      results[page_number][display_class_name][full_id].append(elem)
    self.window_search_rule.add_match_to_results = add_match_to_results

  def get_results(self) -> typing.Dict[str, typing.Any]:
    if self.rows is None:
      return {}
    return {
      self.description: {
        "header": self.header_row,
        "rows": self.rows,
      }
    }

class DoorScheduleSearchRule(PageRecognizerRule):
  def __init__(self, door_search_rule: RegexShapeSearchRule) -> None:
    self.door_search_rule = door_search_rule
    self.description = "doorSchedule"
    self.header_row = None
    self.rows = None

  def process_page(self, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    header_row, rows = pdfextracter.extract_table(
      indexer=indexer,
      text_key="door schedule",
      has_header=True,
      header_above_table=False
    )
    if header_row is not None:
      self.header_row = header_row
    if rows is not None:
      self.rows = rows

      def add_match_to_results(
        results: MultiClassSearchRuleResults,
        page_number: int,
        class_name: str,
        elem_type: str,
        elem: LTJsonResponse
      ):
        full_id = class_name + elem_type
        results[page_number][full_id][full_id].append(elem)
      self.door_search_rule.add_match_to_results = add_match_to_results

  def get_results(self) -> typing.Dict[str, typing.Any]:
    return {
      self.description: {
        "header": self.header_row,
        "rows": self.rows,
      }
    }

class LightingScheduleSearchRule(PageRecognizerRule):
  def __init__(self) -> None:
    self.description = "lightingSchedule"
    self.header_row = None
    self.rows = None

  def process_page(self, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    header_row, rows = pdfextracter.extract_table(
      indexer=indexer,
      text_key="lighting legend",
      has_header=True,
      header_above_table=True
    )
    if header_row is not None:
      self.header_row = header_row,
    if rows is not None:
      self.rows = rows

  def get_results(self) -> typing.Dict[str, typing.Any]:
    if self.rows is None:
      return {}
    return {
      self.description: {
        "header": self.header_row,
        "rows": self.rows,
      }
    }

class PageNameSearchRule(PageRecognizerRule):
  def __init__(self, description: str) -> None:
    self.page_names: typing.Dict[int, str] = {}
    self.description = description

  def process_page(self, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    page_name = pdfextracter.extract_page_name(indexer=indexer)
    self.page_names[page_number] = page_name

  def get_results(self) -> typing.Dict[str, typing.Any]:
    return {
      self.description: self.page_names
    }

class VoteSearcher:
  def __init__(self,
    search_rules: typing.List[SearchRule],
    page_rules: typing.List[PageRecognizerRule],
  ) -> None:
    self.search_rules = search_rules
    self.page_rules = page_rules

  def process_page(
    self,
    page_number: int,
    elems: typing.List[LTJson],
    indexer: pdfindexer.PdfIndexer
  ):
    for rule in self.page_rules:
      rule.process_page(page_number=page_number, indexer=indexer)
    for elem in elems:
      for rule in self.search_rules:
        rule.process_elem(elem=elem, page_number=page_number, indexer=indexer)

  def refine(self) -> None:
    return

  def get_results(self):
    results: typing.Dict[str, typing.Any] = {}
    for rule in self.search_rules + self.page_rules:
      rule_results = rule.get_results()
      merge(dest=results, other=rule_results)
    return results
