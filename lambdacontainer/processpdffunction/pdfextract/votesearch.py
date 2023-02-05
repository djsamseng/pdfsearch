
from abc import ABCMeta, abstractmethod
import collections
import functools
import json
import os
import re
import typing
import uuid

import rtree

from . import pdfindexer, pdfextracter
from .ltjson import LTJson, BboxType, PdfElem, PdfSchedule, PdfScheduleCell, PdfScheduleRow,\
   PdfScheduleCellMatchCriteria, PdfSummaryJson, PdfSummaryJsonItem, PdfSummaryJsonSchedules, \
    PdfItemPtr, ScheduleTypes

def get_uuid() -> str:
  return uuid.uuid4().hex

def item_is_multiline_text(item: PdfElem):
  if len(item["label"]) > 0:
    item_newline = item["label"].find("\n")
    item_multiline = item_newline >= 0 and \
      item_newline - 1 < len(item["label"])
    return item_multiline
  return False

def remove_duplicate_bbox_orig(items: typing.List[PdfElem]):
  bbox_indexer = rtree.index.Index()
  idx = 0
  radius = 0
  out: typing.List[PdfElem] = []
  should_swap_out: typing.List[bool] = []
  for item in items:
    results = bbox_indexer.intersection(item["bbox"])
    if results is not None:
      results = list(results)
    if results is not None and len(results) == 1:
      idx = results[0]
      if should_swap_out[idx]:
        out[idx] = item
    if results is None or len(list(results)) == 0:
      x0, y0, x1, y1 = item["bbox"]
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
      typing.List[PdfElem]
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
    elif isinstance(val, list):
      if key not in dest:
        dest[key] = [] # TODO: Not being merged correctly
      dest[key].extend(other[key])
    elif isinstance(val, str) and len(val) == 0:
      dest[key] = val
    else:
      print("TODO: merge onConflict", dest, other)
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
    regex: typing.Union[None, str],
    shape_matches: typing.List[LTJson] # TODO: Replace with just the shape
  ) -> None:
    self.row_ptr = row_ptr
    self.regex = re.compile(regex) if regex is not None else None
    self.shape_matches = shape_matches
    self.radius = max([max(s.width, s.height) for s in shape_matches])
    self.results: typing.List[PdfElem] = []

  def process_page(self, page_number: int, elems: typing.List[LTJson], indexer: pdfindexer.PdfIndexer):
    self.results = []
    for elem in elems:
      self.__process_elem(elem=elem, page_number=page_number, indexer=indexer)

  def get_results(self) -> typing.List[PdfElem]:
    self.__refine()
    return self.results

  def __process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    if elem.text is None:
      return
    if self.regex is None:
      return
    match = self.regex.search(elem.text)
    if match is None:
      return
    groups = match.groupdict()
    label = groups["label"]
    around_bbox = (
      elem.bbox[0] - self.radius,
      elem.bbox[1] - self.radius,
      elem.bbox[2] + self.radius,
      elem.bbox[3] + self.radius,
    )
    around_elems = indexer.find_contains(bbox=around_bbox)
    for shape in self.shape_matches:
      matching_curves = pdfindexer.find_similar_curves(
        wrapper_to_find=shape,
        wrappers_to_search=around_elems,
        max_dist=2.
      )
      if len(matching_curves) > 0:
        pdf_elem: PdfElem = {
          "label": label,
          "bbox": elem.bbox,
          "rowPtr": self.row_ptr
        }
        self.results.append(pdf_elem)

  def __refine(self):
    self.results = remove_duplicate_bbox_orig(items=self.results)

class ScheduleSearchRule(SearchRule):
  def __init__(
    self,
    table_text_key:str,
    destination: ScheduleTypes,
    elem_shape_matches: typing.Union[None, typing.List[LTJson]],
    elem_label_regex_maker: typing.Union[None, typing.Callable[[str], str]]
  ) -> None:
    self.table_text_key = table_text_key
    self.destination = destination
    self.elem_shape_matches = elem_shape_matches
    self.elem_label_regex_maker = elem_label_regex_maker
    self.item_search_rules: typing.List[ItemSearchRule] = []
    self.results: PdfSummaryJson = make_empty_pdfsummarryjson()

  def process_page(
    self,
    page_number: int,
    elems: typing.List[LTJson],
    indexer: pdfindexer.PdfIndexer
  ) -> None:
    header_row, rows = pdfextracter.extract_table(
      indexer=indexer,
      text_key=self.table_text_key,
      has_header=True,
      header_above_table=False,
    )
    if header_row is not None and rows is not None:
      self.__insert_new_schedule(page_number=page_number, header_row=header_row, rows=rows)

    print(self.destination, len(self.item_search_rules))
    for item_search_rule in self.item_search_rules:
      self.__process_search_rule(
        item_search_rule=item_search_rule,
        page_number=page_number,
        elems=elems,
        indexer=indexer
      )

  def get_results(self) -> PdfSummaryJson:
    return self.results

  def __insert_new_schedule(
    self,
    page_number: int,
    header_row: typing.List[pdfextracter.ExtractedRowElem],
    rows: typing.List[typing.List[pdfextracter.ExtractedRowElem]]
  ) -> None:
    self.item_search_rules = []
    header_row_id = get_uuid()
    self.results["schedules"][self.destination.value][page_number] = {
      "headerRowPtr": {
        "page": page_number,
        "id": header_row_id,
      },
      "rowsRowPtrs": []
    }
    for row in rows:
      id_col_value = row[0]
      row_id = get_uuid()
      self.results["schedules"][self.destination.value][page_number]["rowsRowPtrs"].append({
        "page": page_number,
        "id": row_id
      })
      if page_number not in self.results["items"]:
        self.results["items"][page_number] = {
          "elems": {},
          "cells": {},
          "rows": {},
        }
      self.results["items"][page_number]["rows"][row_id] = {
        "elems": [],
        "cells": [],
      }
      for idx in range(len(header_row)):
        cell_id = get_uuid()
        self.results["items"][page_number]["cells"][cell_id] = {
          "key": header_row[idx].text,
          "label": row[idx].text,
          "bbox": row[idx].bbox,
          "rowPtr": {
            "page": page_number,
            "id": row_id
          },
          "matchCriteria": None
        }
        self.results["items"][page_number]["rows"][row_id]["cells"].append({
          "page": page_number,
          "id": cell_id,
        })
      elem_label_regex = None
      if self.elem_label_regex_maker is not None:
        elem_label_regex = "^(?P<label>{0})".format(
          self.elem_label_regex_maker(id_col_value.text)
        )
      if self.elem_shape_matches is not None:
        elem_shape_matches = self.elem_shape_matches
      else:
        # TODO extract from table
        elem_shape_matches = []
      # TODO: have a single ItemSearchRule per schedule that maps to results
      self.item_search_rules.append(ItemSearchRule(
        row_ptr={
          "page": page_number,
          "id": row_id,
        },
        regex=elem_label_regex,
        shape_matches=elem_shape_matches,
      ))

  def __process_search_rule(
    self,
    item_search_rule: ItemSearchRule,
    page_number: int,
    elems: typing.List[LTJson],
    indexer: pdfindexer.PdfIndexer
  ) -> None:
    item_search_rule.process_page(page_number=page_number, elems=elems, indexer=indexer)
    item_results = item_search_rule.get_results()
    for item_result in item_results:
      row_ptr_page_number = item_result["rowPtr"]["page"]
      row_ptr_id = item_result["rowPtr"]["id"]
      item_id = get_uuid()
      self.results["items"][row_ptr_page_number]["rows"][row_ptr_id]["elems"].append({
        "page": page_number,
        "id": item_id
      })
      if page_number not in self.results["items"]:
        self.results["items"][page_number] = {
          "elems": {},
          "rows": {},
          "cells": {},
        }
      self.results["items"][page_number]["elems"][item_id] = item_result

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
    self.search_rules: typing.List[ScheduleSearchRule] = [
      ScheduleSearchRule(
        table_text_key="door schedule",
        destination=ScheduleTypes.DOORS,
        elem_shape_matches=[global_symbols["door_label"][0]],
        elem_label_regex_maker=lambda id_row_text: id_row_text,
      ),
      ScheduleSearchRule(
        table_text_key="window schedule",
        destination=ScheduleTypes.WINDOWS,
        elem_shape_matches=[global_symbols["window_label"][0]],
        elem_label_regex_maker=lambda id_row_text: id_row_text.replace("##", "\\d\\d")
      )
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
