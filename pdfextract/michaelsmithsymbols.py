
import collections
import os
import time
import typing
import argparse
import json
import gzip
import re

import numpy as np
import pdfminer.high_level

from . import debug_utils
from . import pdfelemtransforms
from . import pdfextracter
from . import pdfindexer
from . import pdftkdrawer
from . import votesearch
from .ltjson import LTJson, LTJsonResponse, LTJsonEncoder

def find_contains_with_room(
  indexer: pdfindexer.PdfIndexer,
  x0:int,
  y0:int,
  x1: int,
  y1: int,
  room: int = 0
):
  y0 -= room
  x0 -= room
  y1 += room
  x1 += room
  matches = indexer.find_contains(bbox=(x0, y0, x1, y1), y_is_down=True)
  return matches

def get_construction_plan_notes_circle(indexer: pdfindexer.PdfIndexer):
  y0, x0 = 1559, 1831
  y1, x1 = 1588, 1859
  matches = find_contains_with_room(indexer=indexer, x0=x0, y0=y0, x1=x1, y1=y1)
  return matches[-1:]

def get_window_label_symbol(indexer: pdfindexer.PdfIndexer):
  y0, x0 = 1755, 1393
  y1, x1 = 1781, 1417
  matches = find_contains_with_room(indexer=indexer, x0=x0, y0=y0, x1=x1, y1=y1)
  return matches[-1:]

def get_window_symbol(indexer: pdfindexer.PdfIndexer):
  y0, x0 = 1695, 1366
  y1, x1 = 1802, 1391
  matches = find_contains_with_room(indexer=indexer, x0=x0, y0=y0, x1=x1, y1=y1)
  # TODO: Allow different sizes and rotations of windows
  return matches

def get_door_label_symbol(indexer: pdfindexer.PdfIndexer):
  y0, x0 = 1458, 894
  y1, x1 = 1480, 924
  matches = find_contains_with_room(indexer=indexer, x0=x0, y0=y0, x1=x1, y1=y1)
  return matches[-1:]

def get_door_symbol(indexer: pdfindexer.PdfIndexer):
  y0, x0 = 1459, 882
  y1, x1 = 1511, 938
  matches = find_contains_with_room(indexer=indexer, x0=x0, y0=y0, x1=x1, y1=y1)
  # TODO: Allow different sizes and rotations of doors
  return matches[6:]

def get_sink_symbol(indexer: pdfindexer.PdfIndexer):
  y0, x0 = 1716, 1039
  y1, x1 = 1750, 1066
  matches = find_contains_with_room(indexer=indexer, x0=x0, y0=y0, x1=x1, y1=y1)
  return matches

def get_toilet_symbol(indexer: pdfindexer.PdfIndexer):
  y0, x0 = 858, 258
  y1, x1 = 909, 288
  matches = find_contains_with_room(indexer=indexer, x0=x0, y0=y0, x1=x1, y1=y1)
  return matches

def get_pdf(which:int = 0, page_number:typing.Union[int, None]=None):
  if which == 0:
    page_number = 9 if page_number is None else page_number
    page_gen = pdfminer.high_level.extract_pages(pdf_file="./plan.pdf", page_numbers=[page_number])
  else:
    page_number = 1 if page_number is None else page_number
    page_gen = pdfminer.high_level.extract_pages(pdf_file="./planMichaelSmith2.pdf", page_numbers=[page_number])
  pages = list(page_gen)
  page = pages[0]
  width = int(page.width)
  height = int(page.height)
  elem_wrappers = pdfelemtransforms.get_underlying_parent_links(elems=page)
  return elem_wrappers, width, height

def get_all_symbols(save: bool):
  wrappers, width, height = get_pdf()
  indexer = pdfindexer.PdfIndexer(wrappers=wrappers, page_width=width, page_height=height)
  # symbol = drawing, label = circle
  notes_circle = get_construction_plan_notes_circle(indexer=indexer)
  window_label = get_window_label_symbol(indexer=indexer)
  window_symbol = get_window_symbol(indexer=indexer) # TODO: different sizes
  door_label = get_door_label_symbol(indexer=indexer)
  door_symbol = get_door_symbol(indexer=indexer) # TODO: different sizes
  sink_symbol = get_sink_symbol(indexer=indexer)
  toilet_symbol = get_toilet_symbol(indexer=indexer)

  all_symbols: typing.Dict[str, typing.List[LTJson]] = {
    "notes_circle": notes_circle,
    "window_label": window_label,
    "window_symbol": window_symbol,
    "door_label": door_label,
    "door_symbol": door_symbol,
    "sink_symbol": sink_symbol,
    "toilet_symbol": toilet_symbol,
  }
  if save:
    encoder = LTJsonEncoder()
    json_string = encoder.encode(all_symbols)
    with open("./lambdacontainer/processpdffunction/symbols_michael_smith.json", "w", encoding="utf-8") as f:
      f.write(json_string)
  else:
    for key, symbol in all_symbols.items():
      drawer = pdftkdrawer.TkDrawer(width=width, height=height)
      drawer.draw_elems(elems=symbol, align_top_left=True)
      drawer.show(key)

def read_symbols_from_json(dirpath:str="./lambdacontainer/processpdffunction/"):
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

def find_symbol():
  symbols = read_symbols_from_json()
  elems, width, height = get_pdf()
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  response_obj: typing.Dict[str, typing.Dict[str, typing.List[LTJsonResponse]]] = {}
  simple_response_obj: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
  page_response_obj: typing.Dict[str, typing.List[LTJsonResponse]] = {}
  simple_page_response_obj: typing.Dict[str, typing.Any] = {}
  for symbol_key in ["door_label", "window_label"]:
    # notes_circle, door_label fails because of "c" curves
    to_find = symbols[symbol_key][0]
    results, result_inner_contents = pdfindexer.find_symbol_with_text(symbol=to_find, indexer=indexer)
    result_response = [LTJsonResponse(elem=elem) for elem in results]
    page_response_obj[symbol_key] = result_response
    labels = [elem.label for elem in result_response]
    simple_page_response_obj[symbol_key] = len(labels)
    print(symbol_key, len(results))
    if False:
      drawer_all = pdftkdrawer.TkDrawer(width=width, height=height)
      drawer_all.draw_elems(elems=elems, draw_buttons=False)
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    to_draw = [elem for elem in results]
    to_draw.extend(result_inner_contents)
    drawer.draw_elems(elems=to_draw, draw_buttons=True)
    drawer.show(symbol_key)

  response_obj["page9"] = page_response_obj
  simple_response_obj["page9"] = simple_page_response_obj
  encoder = LTJsonEncoder()
  json_string = encoder.encode(response_obj)
  compressed_string = gzip.compress(bytes(json_string, "utf-8"))
  simple_json_string = encoder.encode(simple_response_obj)
  simple_compressed_string = gzip.compress(bytes(simple_json_string, "utf-8"))
  # 1kb per symbol per page, 10k pdfs per GB
  # $0.13 per RCU per hour
  print(json_string)
  print(simple_json_string)
  print(len(json_string), len(json_string.encode("utf-8"))/1000, "kb", len(compressed_string)/1000, "kb")
  print(len(simple_json_string), len(simple_json_string.encode("utf-8"))/1000, "kb", len(simple_compressed_string)/1000, "kb")


def show_inside(y0: float, x0: float, y1: float, x1: float):
  elems, width, height = get_pdf()
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  results = indexer.find_contains(bbox=(x0, y0, x1, y1), y_is_down=True)
  print(results)
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=results, draw_buttons=True)
  drawer.show("All")

def find_symbol_elem(y0: float, x0: float, y1: float, x1: float):
  elems, width, height = get_pdf(which=1)
  symbols = read_symbols_from_json()
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  results = indexer.find_contains(bbox=(x0, y0, x1, y1), y_is_down=True)
  to_find = [r for r in results if r.original_path is not None]
  print("Num in area:", len(results), "Num curves in area:", len(to_find))
  to_find = to_find[0]
  results, result_inner_contents = pdfindexer.find_symbol_with_text(symbol=to_find, indexer=indexer)
  print("Searched for:", to_find.get_zeroed_path_lines())
  saved_to_find = symbols["door_label"][0]
  print("Saved door symbol:", saved_to_find.get_zeroed_path_lines())
  mismatch_dist = pdfindexer.line_set_distance(lines1=to_find.get_zeroed_path_lines(), lines2=saved_to_find.get_zeroed_path_lines(), max_dist=1000)
  print("Mismatch dist:", mismatch_dist)
  print("bboxes:", to_find.get_zeroed_bbox(), saved_to_find.get_zeroed_bbox())
  elems2, w2, h2 = get_pdf(which=0)
  indexer2 = pdfindexer.PdfIndexer(wrappers=elems2, page_width=w2, page_height=h2)
  saved_to_find_orig = get_door_label_symbol(indexer=indexer2)
  print(len(to_find.get_zeroed_path_lines()), len(saved_to_find.get_zeroed_path_lines()))
  # Different lengths, to_find uses c curves. saved_to_find uses just m and l
  # Even though they have different zeroed lines, they do draw very similarly
  #print("To find:", to_find.original_path)
  #print("Saved:", saved_to_find.original_path)
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  to_draw = [elem for elem in results]
  to_draw.extend(result_inner_contents)
  print(to_find.original_path)
  drawer.draw_elems(elems=[to_find, saved_to_find, saved_to_find_orig[0]], draw_buttons=True, align_top_left=True)
  drawer.show("Found")

def door_labels_should_match():
  match_window_circle_lines_only = False
  if match_window_circle_lines_only:
    y0, x0, y1, x1 = 306, 549, 329, 579
  else:
    y0, x0, y1, x1 = 870, 611, 896, 646
  elems, width, height = get_pdf(which=1)
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  results = indexer.find_contains(bbox=(x0, y0, x1, y1), y_is_down=True)
  symbols = read_symbols_from_json()
  curve = symbols["door_label"][0]
  path = curve.original_path
  if match_window_circle_lines_only:
    curve2 = results[0]
  else:
    curve2 = results[-1]
  path2 = curve2.original_path
  print("=== Path 1 ===")
  print(path)
  print("=== Path 2 ===")
  print(path2)
  print("=== Lines 1 ===")
  print(curve.get_zeroed_path_lines())
  print("=== Lines 2 ===")
  print(curve2.get_zeroed_path_lines())

  matches = pdfindexer.find_similar_curves(wrapper_to_find=curve, wrappers_to_search=[curve2], max_dist=2)
  print("Matches:", len(matches))
  return

  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=[curve], align_top_left=True)
  drawer2 = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer2.draw_elems(elems=[curve2], align_top_left=True)

  drawer.show("")


def showall():
  elems, width, height = get_pdf(which=1)
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=elems, draw_buttons=False)
  drawer.show("All")

def elems_not_equal(elems: typing.List[LTJson]):
  for idx1 in range(len(elems)):
    if idx1 == 16449 or idx1 == 20620:
      continue
    if idx1 == 17218 or idx1 == 21130:
      continue
    for idx2 in range(len(elems)):
      if idx1 != idx2:
        if elems[idx1] == elems[idx2]:
          print("idx1={0} idx2={1} elem1={2} elem2={3}".format(idx1, idx2, elems[idx1], elems[idx2]))
          return False
  return True

def test_encode_decode():
  debug_utils.is_debug = True
  elem_wrappers, _, _ = get_pdf()
  encoder = LTJsonEncoder()
  json_string = encoder.encode(elem_wrappers)

  elem_dicts = json.loads(json_string)
  np.testing.assert_allclose(len(elem_dicts), len(elem_wrappers))
  elems = [LTJson(serialized_json=elem) for elem in elem_dicts]
  for idx in range(len(elems)):
    if elems[idx] != elem_wrappers[idx]:
      print("Not equal:", elems[idx], elem_wrappers[idx])
      return

  np.testing.assert_array_equal(elems, elem_wrappers) # type: ignore
  assert elems == elem_wrappers
  if True:
    print("Checking no equal elements out of {0}".format(len(elems)))
    elems_not_equal(elems=elems)

def print_indent(d: votesearch.MergeDict, level: int = 0):
  for key, val in d.items():
    if isinstance(val, (dict, collections.defaultdict)):
      print(" " * level + key)
      print_indent(d=typing.cast(votesearch.MergeDict, val), level=level+1)
    elif isinstance(val, list):
      val = typing.cast(typing.List[LTJson], val)
      print(" " * level + key, ":", [v.text for v in val])

def find_by_bbox_and_content_search_rule():
  t0 = time.time()
  symbols = read_symbols_from_json()
  search_rules: typing.List[votesearch.SearchRule] = [
    votesearch.RegexShapeSearchRule(shape_matches=[
      symbols["window_label"][0],
    ], description="windows", regex="(?P<class_name>[a-zA-Z])(?P<elem_type>\\d\\d)"),
    votesearch.RegexShapeSearchRule(shape_matches=[
      symbols["door_label"][0],
    ], description="doors", regex="(?P<class_name>\\d)(?P<elem_type>\\d\\d)")
  ]
  t1 = time.time()
  elems, width, height = get_pdf(which=1)
  t2 = time.time()
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  vote_searcher = votesearch.VoteSearcher(search_rules=search_rules, page_rules=[])

  vote_searcher.process_page(page_number=2, elems=elems, indexer=indexer)
  vote_searcher.refine()
  all_results = vote_searcher.get_results()
  t3 = time.time()
  for key, results in all_results.items():
    print(key)
    print_indent(results, level=1)

  print("Took:", t3-t2 + t1-t0)

  def draw_results(results: typing.Dict[str, typing.Any]):
    all_found: typing.List[typing.Any] = []
    for _, val in results.items():
      for _, valwt in val.items():
        for _, valwid in valwt.items():
          all_found.extend(valwid)
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    drawer.draw_elems(elems=all_found, draw_buttons=True, align_top_left=False)
    drawer.show("")

  for results in all_results.values():
    draw_results(results)

  # weird = all_results["windows"]["Page 2"]["F"]["01"]


def find_by_bbox_and_content():

  t0 = time.time()
  symbols = read_symbols_from_json()
  t1 = time.time()
  search_symbols = {
    "window_label": pdfindexer.SearchSymbol(
      elem=symbols["window_label"][0],
      description="window_label",
      inside_text_regex_str="[a-zA-Z]\\d\\d"
    ),
    "door_label": pdfindexer.SearchSymbol(
      elem=symbols["door_label"][0],
      description="door_label",
      inside_text_regex_str="\\d\\d\\d"
    )
  }
  t2 = time.time()
  elems, width, height = get_pdf(which=1)
  t3a = time.time()
  items_indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  search_indexer = pdfindexer.SearchIndexer(search_items=list(search_symbols.values()), items_indexer=items_indexer)
  t3b = time.time()
  found_results: typing.Dict[str, typing.List[LTJson]] = {
    "window_label": [],
    "door_label": []
  }
  for elem in elems:
    recognized_symbols = search_indexer.match_distance(search_elem=elem, query_radius=1)
    if len(recognized_symbols) > 1:
      print("==== Matched Both ====")
    for rec in recognized_symbols:
      found_results[rec.description].append(elem)
  t4 = time.time()
  for symbol_name, symbol_matches in found_results.items():
    print(symbol_name, ":", len(symbol_matches))

  t5 = time.time()
  print(pdfextracter.extract_page_name(indexer=items_indexer))
  t6 = time.time()
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  to_draw: typing.List[LTJson] = []
  for val in found_results.values():
    to_draw.extend(val)
  drawer.draw_elems(elems=to_draw, draw_buttons=True, align_top_left=False)
  t7 = time.time()
  print("read:", t1-t0, "symbol creation:", t2-t1, "getpdf:", t3a-t2, "indexer creation:", t3b-t3a,
    "distance match:", t4-t3b, "page name extraction:", t6-t5, "drawing:", t7-t6
  )
  drawer.show("Found")

def findmeta():
  elems, width, height = get_pdf(which=1)
  items_indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  page_name = pdfextracter.extract_page_name(indexer=items_indexer)
  house_name = None
  for elem in elems:
    potential_house_name = pdfextracter.extract_house_name( # type: ignore
      regex=re.compile("^project name.{0,2}"),
      elem=elem,
      indexer=items_indexer
    )
    if potential_house_name is not None:
      house_name = potential_house_name
  print("Found page name: '{0}'".format(page_name))
  print("Found house name: '{0}'".format(house_name))

def line_slope(elem: LTJson):
  x0, y0, x1, y1 = elem.bbox
  return (y1 - y0) / x1 - x0

def findschedule():
  elems, width, height = get_pdf(which=1, page_number=1)
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  header_row, rows = pdfextracter.extract_table(
    indexer=indexer,
    text_key="window schedule",
    has_header=True,
    header_above_table=False
  )

  print(header_row)
  print(rows)
  if header_row is None or rows is None:
    return
  print([len(row) for row in rows], len(header_row))
  # go row to row left to right extracting each row

  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=elems, draw_buttons=False, align_top_left=True)
  drawer.show("Below")

def findlighting():
  elems, width, height = get_pdf(which=1, page_number=2)
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  header_row, rows = pdfextracter.extract_table(
    indexer=indexer,
    text_key="lighting legend",
    has_header=True,
    header_above_table=True,
  )
  # RECT = top horizontal line + 3 lines in one
  # vs RECT = window schedule = 4 lines in one
  print(header_row)
  print(rows)
  if header_row is None or rows is None:
    return
  print([len(row) for row in rows], len(header_row))

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--getall", dest="getall", default=False, action="store_true")
  parser.add_argument("--test", dest="test", default=False, action="store_true")
  # Save the results to a file
  parser.add_argument("--save", dest="save", default=False, action="store_true")
  # Take the saved file and upload
  parser.add_argument("--upload", dest="upload", default=False, action="store_true")
  parser.add_argument("--find", dest="find", default=False, action="store_true")
  parser.add_argument("--showall", dest="showall", default=False, action="store_true")
  parser.add_argument("--findbbox", dest="findbbox", default=False, action="store_true")
  parser.add_argument("--findmeta", dest="findmeta", default=False, action="store_true")
  parser.add_argument("--findschedule", dest="findschedule", default=False, action="store_true")
  parser.add_argument("--findlighting", dest="findlighting", default=False, action="store_true")
  parser.add_argument("--x0", dest="x0", type=int, required=False)
  parser.add_argument("--y0", dest="y0", type=int, required=False)
  parser.add_argument("--x1", dest="x1", type=int, required=False)
  parser.add_argument("--y1", dest="y1", type=int, required=False)
  return parser.parse_args()

def main():
  args = parse_args()
  if args.test:
    test_encode_decode()
  elif args.showall:
    showall()
  elif args.x0 is not None and args.y0 is not None and args.x1 is not None and args.y1 is not None:
    # python3 michaelsmithsymbols.py --y0 306 --x0 549 --y1 329 --x1 579
    if args.find:
      find_symbol_elem(y0=args.y0, x0=args.x0, y1=args.y1, x1=args.x1)
    else:
      show_inside(y0=args.y0, x0=args.x0, y1=args.y1, x1=args.x1)
  elif args.find:
    find_symbol()
  elif args.findbbox:
    find_by_bbox_and_content_search_rule()
  elif args.getall:
    get_all_symbols(save=args.save)
  elif args.findmeta:
    findmeta()
  elif args.findschedule:
    findschedule()
  elif args.findlighting:
    findlighting()
  else:
    door_labels_should_match()


if __name__ == "__main__":
  # python3 -m pdfextract.michaelsmithsymbols --findbbox
  main()