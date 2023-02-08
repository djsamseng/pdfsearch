
from abc import ABCMeta, abstractmethod
import collections
import functools
import json
import os
import re
import typing
import uuid

import rtree

from . import pdfindexer, pdfextracter, pdfelemtransforms
from .ltjson import LTJson, BboxType, PdfElem, PdfSchedule, PdfScheduleCell, PdfScheduleRow,\
   PdfSummaryJson, PdfRowPtr, ScheduleTypes

def get_uuid() -> str:
  return uuid.uuid4().hex

def item_is_multiline_text(item: PdfElem):
  if len(item["label"]) > 0:
    item_newline = item["label"].find("\n")
    item_multiline = item_newline >= 0 and \
      item_newline - 1 < len(item["label"])
    return item_multiline
  return False

def remove_duplicate_bbox(items: typing.List[PdfElem]):
  def item_size(item: PdfElem):
    x0, y0, x1, y1 = item["bbox"]
    return (x1-x0) * (y1-y0)
  items.sort(key=lambda x: item_size(x), reverse=True) # pylint:disable=unnecessary-lambda

  bbox_indexer = rtree.index.Index()
  out: typing.List[PdfElem] = []
  idx = 0
  radius = 0
  def insert_item(item: PdfElem):
    x0, y0, x1, y1 = item["bbox"]
    bbox = (x0-radius, y0-radius, x1+radius, y1+radius)
    bbox_indexer.insert(idx, bbox)
    out.append(item)
  for item in items:
    results = bbox_indexer.intersection(item["bbox"])
    if results is None:
      insert_item(item)
    else:
      results = list(results)
      if len(results) == 0:
        insert_item(item)
      else:
        overlaps_a_result = False
        for result in results:
          overlap = pdfelemtransforms.bbox_intersection_area(a=out[result]["bbox"], b=item["bbox"])
          width = item["bbox"][2] - item["bbox"][0]
          height = item["bbox"][3] - item["bbox"][1]
          if overlap > width * height * 0.9:
            overlaps_a_result = True
            break
        if not overlaps_a_result:
          insert_item(item)
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
    if key not in dest:
      dest[key] = val
    elif isinstance(val, (dict, collections.defaultdict)):
      node = dest.setdefault(key, {})
      merge_impl(dest=node, other=typing.cast(MergeDict, val))
    elif isinstance(val, list):
      dest[key].extend(other[key])
    elif isinstance(val, str) and len(dest[key]) == 0:
      dest[key] = val
    else:
      print("TODO: merge onConflict", dest, other, key)
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
    "doors": {},
    "windows": {},
    "lighting": {},
    "houseName": "",
    "architectName": "",
    "pageNames": {}
  }

def shape_group_matches(
  shape_group: typing.List[LTJson],
  to_search: typing.List[LTJson]
) -> typing.List[LTJson]:
  if len(shape_group) == 0 or len(to_search) == 0:
    return []
  all_matching_curves: typing.List[LTJson] = []
  for shape in shape_group:
    # TODO: Only find similar curves that have not already been used (ex: double circle)
    matching_curves = pdfindexer.find_most_similar_curve(
      wrapper_to_find=shape,
      wrappers_to_search=to_search,
      max_dist=2.
    )
    all_matching_curves.extend(matching_curves)
    if len(matching_curves) == 0:
      return []
  return all_matching_curves

class ItemSearchRule(SearchRule):
  def __init__(
    self,
    row_ptr: PdfRowPtr,
    regex: typing.Union[None, str],
    # Match one of the outer list of all of the inner list
    shape_matches: typing.List[typing.List[LTJson]]
  ) -> None:
    self.row_ptr = row_ptr
    self.regex = re.compile(regex) if regex is not None else None
    self.shape_matches = shape_matches
    self.results: typing.List[PdfElem] = []
    if len(self.shape_matches) == 0:
      return

    self.bounding_box = pdfelemtransforms.bounding_bbox_nested(nested=self.shape_matches)
    self.radius = max(
      self.bounding_box[2] - self.bounding_box[0],
      self.bounding_box[3] - self.bounding_box[1]
    ) + 10

  def process_page(self, page_number: int, elems: typing.List[LTJson], indexer: pdfindexer.PdfIndexer):
    if len(self.shape_matches) == 0:
      return
    self.results = []
    for elem in elems:
      self.__process_elem(elem=elem, page_number=page_number, indexer=indexer)

  def get_results(self) -> typing.List[PdfElem]:
    self.__refine()
    return self.results

  def __process_elem(self, elem: LTJson, page_number: int, indexer: pdfindexer.PdfIndexer) -> None:
    around_bbox = (
      elem.bbox[0] - self.radius,
      elem.bbox[1] - self.radius,
      elem.bbox[2] + self.radius,
      elem.bbox[3] + self.radius,
    )
    if self.regex is not None:
      if elem.text is None:
        return
      match = self.regex.search(elem.text)
      if match is None:
        return
      groups = match.groupdict()
      label = groups["label"]
      if len(label) == 0:
        return

      # TODO: Need voting since regex for "C" can match "CO" and conflict
      # TODO: D8 and D9 page 9 plan.pdf are missing
      # TODO: Need merge filtering to remove similar shapes in odd places
    else:
      return
      # check if the elem matches the first shape match

    #  30847    0.062    0.000    0.103    0.000 layout.py:360(__init__) LTChar
    #   8279    0.003    0.000    0.016    0.000 layout.py:483(__init__) LTTextContainer
    #  76655    0.112    0.000    0.184    0.000 ltjson.py:15(__init__)
    # 108492    0.452    0.000  146.521    0.001 pdfindexer.py:50(find_contains)
    # so at most we need to process 8279 elements
    # But we have 100 regexes which gets to 108492
    # Maybe just making the regex more strict?
    # That gets us down to
    #    294    0.002    0.000    0.275    0.001 pdfindexer.py:50(find_contains)
    around_elems = indexer.find_contains(bbox=around_bbox)
    matched_elems: typing.List[LTJson] = []
    for shape_group in self.shape_matches:
      matching_curves = shape_group_matches(shape_group=shape_group, to_search=around_elems)
      if len(matching_curves) > 0:
        matched_elems.extend(matching_curves)
        break
    if len(matched_elems) > 0:
      matched_elems.append(elem)
      highlight_bbox = pdfelemtransforms.bounding_bbox(matched_elems)
      pdf_elem: PdfElem = {
        "label": label,
        "bbox": highlight_bbox,
        "rowPtr": self.row_ptr
      }
      self.results.append(pdf_elem)

  def __refine(self):
    self.results = remove_duplicate_bbox(items=self.results)

class ScheduleSearchRule(SearchRule):
  def __init__(
    self,
    table_text_key:str,
    destination: ScheduleTypes,
    elem_shape_matches: typing.Union[None, typing.List[typing.List[LTJson]]],
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
      header_above_table=self.destination == ScheduleTypes.LIGHTING,
    )
    if header_row is not None and rows is not None:
      self.__insert_new_schedule(page_number=page_number, header_row=header_row, rows=rows)

    for item_search_rule in self.item_search_rules:
      self.__process_search_rule(
        item_search_rule=item_search_rule,
        page_number=page_number,
        elems=elems,
        indexer=indexer
      )

  def get_results(self) -> PdfSummaryJson:
    return self.results

  def __get_row_cells(
    self,
    page_number: int,
    row_idx: int,
    row: typing.List[pdfextracter.ExtractedRowElem],
    header_row: typing.List[pdfextracter.ExtractedRowElem],
  ) -> typing.List[PdfScheduleCell]:
    out: typing.List[PdfScheduleCell] = []
    for idx in range(len(header_row)):
      new_cell: PdfScheduleCell = {
        "key": header_row[idx].text,
        "label": row[idx].text,
        "bbox": row[idx].bbox,
        "rowPtr": {
          "schedule": self.destination,
          "page": page_number,
          "row": row_idx,
        },
      }
      out.append(new_cell)
    return out

  def __insert_new_schedule(
    self,
    page_number: int,
    header_row: typing.List[pdfextracter.ExtractedRowElem],
    rows: typing.List[typing.List[pdfextracter.ExtractedRowElem]]
  ) -> None:
    self.item_search_rules = []
    self.results[self.destination.value][page_number] = {
      "headerRow": {
        "elems": [],
        "cells": self.__get_row_cells(
          page_number=page_number,
          row_idx=-1,
          row=header_row,
          header_row=header_row,
        ),
      },
      "rows": []
    }
    elem_shape_symbol_col_idx = 0
    for idx in range(len(header_row)):
      if header_row[idx].text.lower().find("symbol") >= 0:
        elem_shape_symbol_col_idx = idx
    for idx, row in enumerate(rows):
      id_col_value = row[0]
      self.results[self.destination.value][page_number]["rows"].append({
        "elems": [],
        "cells": self.__get_row_cells(
          page_number=page_number,
          row_idx=idx,
          row=row,
          header_row=header_row,
        )
      })
      elem_label_regex = None
      if self.elem_label_regex_maker is not None and len(id_col_value.text.strip()) > 0:
        elem_label_regex = "^(?P<label>{0})[\\n ]?$".format(
          self.elem_label_regex_maker(id_col_value.text)
        )
      if self.elem_shape_matches is not None:
        elem_shape_matches = self.elem_shape_matches
      else:
        elem_shape_matches = [row[elem_shape_symbol_col_idx].elems] # Need to match all of 1 option
      self.item_search_rules.append(ItemSearchRule(
        row_ptr={
          "schedule": self.destination,
          "page": page_number,
          "row": idx,
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
      row_ptr_row_idx = item_result["rowPtr"]["row"]
      row_ptr_schedule = item_result["rowPtr"]["schedule"]
      self.results[row_ptr_schedule.value][row_ptr_page_number]["rows"][row_ptr_row_idx]["elems"].append({
          "label": item_result["label"],
          "bbox": item_result["bbox"],
          # rowPtr from the schedule that created the rule not necessarily the current schedule rule
          "rowPtr": item_result["rowPtr"]
        })

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
        elem_shape_matches=[global_symbols["door_label"][0:1]],
        elem_label_regex_maker=lambda id_row_text: id_row_text,
      ),
      ScheduleSearchRule(
        table_text_key="window schedule",
        destination=ScheduleTypes.WINDOWS,
        elem_shape_matches=[global_symbols["window_label"][0:1]],
        elem_label_regex_maker=lambda id_row_text: id_row_text.replace("##", "\\d\\d")
      ),
      ScheduleSearchRule(
        table_text_key="lighting legend",
        destination=ScheduleTypes.LIGHTING,
        elem_shape_matches=None,
        elem_label_regex_maker=lambda id_row_text: id_row_text # TODO: some lighting elements don't have this
      ),
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
