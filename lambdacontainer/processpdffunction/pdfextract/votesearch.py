
from abc import ABCMeta, abstractmethod
import collections
import functools
import os
import re
import typing
import uuid

import rtree

from . import pdfindexer, pdfextracter
from .ltjson import LTJson, BboxType, PdfElem, PdfSchedule, PdfScheduleCell, PdfScheduleRow,\
   PdfScheduleCellMatchCriteria, PdfSummaryJson, PdfSummaryJsonItem, PdfSummaryJsonSchedules, \
    PdfItemPtr

def get_uuid() -> str:
  return uuid.uuid4().hex

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

class RowHeader(typing.TypedDict):
  header: typing.List[str]
  rows: typing.List[typing.List[str]] # TODO: Replace with positions and what they map to etc.

PageScheduleSearchRuleResults = typing.Dict[
  int, # page_number
  RowHeader,
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
        matching_shape: PdfElem = {
          "label": elem.text,
          "bbox": elem.bbox,
          "rowPtr": {
            "page": 0, # page of schedule
            "id": "" # id of schedule row
          }
        }
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

class LightingSearchRule(SearchRule):
  def __init__(self) -> None:
    self.results: MultiClassSearchRuleResults = create_results_dict()
    # TODO: Replace RegexShapeSearchRule with optional regex and the text can be outside but near
    self.search_rules: typing.List[RegexShapeSearchRule] = []

  def process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    for rule in self.search_rules:
      rule.process_elem(elem=elem, page_number=page_number, indexer=indexer)

  def get_results(self) -> typing.Dict[str, typing.Any]:
    results: typing.Dict[str, typing.Any] = {}
    for rule in self.search_rules:
      rule_results = rule.get_results() # description: page: display_class_name: full_id: elem
      merge(dest=results, other=rule_results)
    return results


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
    self.results: PageScheduleSearchRuleResults = {}
    self.header_row = None
    self.rows = None

  def process_page(self, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    header_row, rows = pdfextracter.extract_table(
      indexer=indexer,
      text_key="window schedule",
      has_header=True,
      header_above_table=False,
    )
    if header_row is not None and rows is not None:
      self.results[page_number] = {
        "header": [h.text for h in header_row],
        "rows": [[r.text for r in row] for row in rows],
      }
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
    return {
      self.description: self.results
    }


class LightingScheduleSearchRule(PageRecognizerRule):
  def __init__(self, lighting_search_rule: LightingSearchRule) -> None:
    self.description = "lightingSchedule"
    self.header_row = None
    self.rows = None
    self.lighting_search_rule = lighting_search_rule
    self.used_search_rules: typing.List[SearchRule] = []

  def process_page(self, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    self.lighting_search_rule.search_rules = [] # Reset what to search for
    header_row, rows = pdfextracter.extract_table(
      indexer=indexer,
      text_key="lighting legend",
      has_header=True,
      header_above_table=True,
    )
    if header_row is not None:
      self.header_row = [h.text for h in header_row]
    if rows is not None:
      self.rows = [[r.text for r in row] for row in rows]

    if header_row is not None and rows is not None:
      for idx, row in enumerate(rows):
        def add_match_to_results(
          results: MultiClassSearchRuleResults,
          page_number: int,
          class_name: str,
          elem_type: str,
          elem: LTJsonResponse,
          idx: int
        ):
          # class_name = A B C or empty
          # elem_type = empty
          display_class_name = class_name
          if len(display_class_name.strip()) == 0:
            display_class_name = str(idx)
          full_id = display_class_name
          results[page_number][display_class_name][full_id].append(elem)

        add_match_to_results_bound = functools.partial(add_match_to_results, idx=idx)
        # TODO: parse out shape_matches
        row_rule = RegexShapeSearchRule(shape_matches=row[1].elems, description="lighting", regex="")
        row_rule.add_match_to_results = add_match_to_results_bound
        self.lighting_search_rule.search_rules.append(row_rule)
        self.used_search_rules.append(row_rule)

  def get_results(self) -> typing.Dict[str, typing.Any]:
    if self.rows is None:
      return {}
    out = {
      self.description: {
        "header": self.header_row,
        "rows": self.rows,
      }
    }
    for rule in self.used_search_rules:
      merge(dest=out, other=rule.get_results())
    return out

class PageNameSearchRule(PageSearchRule):
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

class DoorScheduleSearchRule(PageSearchRule):
  def __init__(self) -> None:
    self.elem_search_rule = None
    self.header_row = None
    self.rows = None
    self.items: typing.Dict[int, PdfSummaryJsonItem] = {}

  def process_page(self, page_number: int, indexer: pdfindexer.PdfIndexer) -> typing.List[SearchRule]:
    header_row, rows = pdfextracter.extract_table(
      indexer=indexer,
      text_key="door schedule",
      has_header=True,
      header_above_table=False,
    )
    if header_row is not None and rows is not None:
      self.header_row = [h.text for h in header_row]
      self.rows = [[r.text for r in row] for row in rows]

      self.elem_search_rule = RegexShapeSearchRule(
        shape_matches=[],
        description="",
        regex=""
      )
    if self.elem_search_rule is not None:
      return [self.elem_search_rule]
    return []

  def finish_page(self, page_number: int) -> None:
    items_found = None
    if self.elem_search_rule is not None:
      items_found = self.elem_search_rule.get_and_clear_results()
    if self.header_row is not None and self.rows is not None:


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

import json
def read_symbols_from_json():
  dirpath = "./"
  with open(os.path.join(dirpath, "symbols_michael_smith.json"), "r", encoding="utf-8") as f:
    json_string = f.read()
  symbols_dicts = json.loads(json_string)
  symbols: typing.Dict[str, typing.List[LTJson]] = dict()
  for key, serialized_elems in symbols_dicts.items():
    elems: typing.List[LTJson] = []
    for serialized_json in serialized_elems:
      elems.append(LTJson(serialized_json=serialized_json))
    symbols[key] = elems
  return symbols

global_symbols = read_symbols_from_json()

MergeDict = typing.Dict[str, typing.Any]
def merge_impl(
  dest: MergeDict,
  other: MergeDict
):
  for key, val in other.items():
    if isinstance(val, (dict, collections.defaultdict)):
      node = dest.setdefault(key, {})
      merge_impl(dest=node, other=typing.cast(MergeDict, val))
    elif isinstance(val, str) and len(val) == 0:
      dest[key] = val
    else:
      print("TODO: merge onConflict")
      dest[key] = val

def merge(
  dest: PdfSummaryJson,
  other: PdfSummaryJson
):
  merge_impl(typing.cast(MergeDict, dest), typing.cast(MergeDict, other))


class SearchRule(metaclass=ABCMeta):
  @abstractmethod
  def process_page(
    self,
    page_number: int,
    elems: typing.List[LTJson],
    indexer: pdfindexer.PdfIndexer
  ):
    pass

  @abstractmethod
  def get_results(self) -> typing.Union[PdfSummaryJson, typing.List[PdfElem]]:
    pass

def make_empty_pdfsummarryjson() -> PdfSummaryJson:
  return {
    "items": {},
    "schedules": {
      "doors": {},
      "windows": {},
      "lighting": {},
    },
    "houseName": "",
    "architectName": "",
    "pageNames": {}
  }

class ItemSearchRule(SearchRule):
  def __init__(
    self,
    row_ptr: PdfItemPtr,
    regex: str,
    shape_matches: typing.List[LTJson] # TODO: Replace with just the shape
  ) -> None:
    self.row_ptr = row_ptr

  def process_page(self, page_number: int, elems: typing.List[LTJson], indexer: pdfindexer.PdfIndexer):
    pass

  def get_results(self) -> typing.List[PdfElem]:
    return []


class WindowScheduleSearchRule(SearchRule):
  def __init__(self) -> None:
    self.window_item_search_rules: typing.List[ItemSearchRule] = []
    self.results: PdfSummaryJson = make_empty_pdfsummarryjson()

  def process_page(self, page_number: int, elems: typing.List[LTJson], indexer: pdfindexer.PdfIndexer):
    header_row, rows = pdfextracter.extract_table(
      indexer=indexer,
      text_key="window schedule",
      has_header=True,
      header_above_table=False,
    )
    if header_row is not None and rows is not None:
      for item_search_rule in self.window_item_search_rules:
        rule_results = item_search_rule.get_results()
        for rule_result in rule_results:
          result_id = get_uuid()
          self.results["items"][page_number]["elems"][result_id] = rule_result
      self.window_item_search_rules = []
      header_row_id = get_uuid()
      self.results["schedules"]["windows"][page_number] = {
        "headerRowPtr": {
          "page": page_number,
          "id": header_row_id,
        },
        "rowsRowPtrs": []
      }
      for row in rows:
        id_col_value = row[0]
        row_id = get_uuid()
        self.results["schedules"]["windows"][page_number]["rowsRowPtrs"].append({
          "page": page_number,
          "id": row_id
        })
        for idx in range(len(header_row)):
          cell_id = get_uuid()
          self.results["items"][page_number]["cells"][cell_id] = {
            "key": header_row[idx].text,
            "label": row[idx].text,
            "bbox": row[idx].bbox, # TODO: return bbox
            "rowPtr": {
              "page": page_number,
              "id": row_id
            },
            "matchCriteria": None
          }
        self.window_item_search_rules.append(ItemSearchRule(
          row_ptr={
            "page": page_number,
            "id": row_id,
          },
          regex="^(?P<label>{0})".format(id_col_value.text.replace("##", "\\d\\d")),
          shape_matches=[global_symbols["window_label"][0]]
        ))

    for item_search_rule in self.window_item_search_rules:
      item_search_rule.process_page(page_number=page_number, elems=elems, indexer=indexer)

  def get_results(self) -> PdfSummaryJson:
    return self.results

class PdfSearcher:
  '''
  Layer 1: Look at the page and classify regions of interest
  Layer 2: Extract information from that region
  Layer 3: Vote to see if extracted information makes sense together
  Layer 4: Form a consensus
  Divide Conquer Merge
  Divide - multiple layers = classify regions (ex: layer 1. See Window Schedule layer 2. Find table box 3. Find rows 4. Find cells)
  Conquer - pull out the data and recognize it / associate it with memories
  Merge - Does this data make sense in context? If not, restart the divide, conquer, merge with the additional information
  Essentially this is a neural network view to writing a function that calls sub functions
  However when we divide, we want to pass down what we know (ex: the window schedule)
  So we go elem by elem, hey I might recognize this "W" might start "Window Schedule"!
  Also we might need to do another loop. I recognized a window but I don't know what to do with it until we get the schedule data
  A search rule may create and own sub rules. They are responsible for merging back upward
  '''
  def __init__(
    self
  ) -> None:
    self.search_rules: typing.List[SearchRule] = [

    ]

  def process_page(
    self,
    page_number: int,
    elems: typing.List[LTJson],
    indexer: pdfindexer.PdfIndexer
  ):
    for rule in self.search_rules:
      rule.process_page(page_number=page_number, elems=elems, indexer=indexer)

  def refine(self):
    pass

  def get_results(self) -> PdfSummaryJson:
    results: PdfSummaryJson = make_empty_pdfsummarryjson()
    for rule in self.search_rules:
      rule_results = rule.get_results()
      merge(dest=results, other=rule_results)
    return results
