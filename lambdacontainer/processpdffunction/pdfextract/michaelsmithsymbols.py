
import collections
import cProfile
import os
import pickle
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
from . import dataprovider, pdfprocessor
from .ltjson import LTJson, LTJsonEncoder

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
    with open("./symbols_michael_smith.json", "w", encoding="utf-8") as f:
      f.write(json_string)
  else:
    for key, symbol in all_symbols.items():
      drawer = pdftkdrawer.TkDrawer(width=width, height=height)
      drawer.draw_elems(elems=symbol, align_top_left=True)
      drawer.show(key)

def read_symbols_from_json(dirpath:str="./"):
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

def show_inside(y0: float, x0: float, y1: float, x1: float):
  elems, width, height = get_pdf()
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  results = indexer.find_contains(bbox=(x0, y0, x1, y1), y_is_down=True)
  print(results)
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=results, draw_buttons=True)
  drawer.show("All")

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


def showall(page: typing.Union[int, None] = None):
  elems, width, height = get_pdf(which=0, page_number=page)
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=elems, draw_buttons=False, draw_all_text=False)
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
    header_above_table=False,
  )

  if header_row is not None:
    print([h.text for h in header_row])
  if rows is not None:
    print([[r.text for r in row] for row in rows])
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
  # vs RECT = window schedule = 4 lines in oWne
  if header_row is not None:
    print([h.text for h in header_row])
  if rows is not None:
    print([[r.text for r in row] for row in rows])
  if header_row is None or rows is None:
    return
  print([len(row) for row in rows], len(header_row))
  row_elems: typing.List[LTJson] = []
  for row in rows:
    for r in row:

      row_elems.extend(r.elems)
  print([e.text for e in row_elems])
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=row_elems, draw_buttons=False, align_top_left=True)
  drawer.show("Below")

def compare_windows_doors(
  a: votesearch.MultiClassSearchRuleResults,
  b: votesearch.MultiClassSearchRuleResults,
):
  np.testing.assert_array_equal(list(a.keys()), list(b.keys())) # type:ignore
  for page_key in a.keys():
    a_page_vals = a[page_key]
    b_page_vals = b[page_key]
    np.testing.assert_array_equal(list(a_page_vals.keys()), list(b_page_vals.keys())) # type:ignore
    for class_key in a_page_vals.keys():
      a_class_vals = a_page_vals[class_key]
      b_class_vals = b_page_vals[class_key]
      np.testing.assert_array_equal( # type:ignore
        list(a_class_vals.keys()),
        list(b_class_vals.keys()))
      for id_key in a_class_vals.keys():
        a_id_vals = a_class_vals[id_key]
        b_id_vals = b_class_vals[id_key]
        np.testing.assert_array_equal(a_id_vals, b_id_vals) # type:ignore

# header: [str]
# rows: [[str]]
def compare_schedules(a: typing.Any, b: typing.Any):
  np.testing.assert_array_equal(a["header"], b["header"]) # type:ignore
  np.testing.assert_array_equal(a["rows"], b["rows"]) # type:ignore

def process_pdf_imp():
  debug_utils.is_debug = True
  data_provider = dataprovider.NullDataProvider()
  filename = "plan.pdf"
  with open(filename, mode="rb") as f:
    pdfdata = f.read()
  # Test that the processing results are equivalent
  page_numbers = [2,5,9]
  # page_numbers = None
  t0 = time.time()
  ltjson_results = pdfprocessor.process_pdf(data_provider=data_provider, pdfkey=filename, pdfdata=pdfdata, page_numbers=page_numbers)
  t1 = time.time()
  update_saved = False
  write_pending = True
  if write_pending:
    with open("test2.json", "w", encoding="utf-8") as f:
      f.write(json.dumps(ltjson_results))
  if update_saved:
    encoder = LTJsonEncoder()
    with open("test.json", "w", encoding="utf-8") as f:
      f.write(encoder.encode(ltjson_results))

  print("process_pdf took:", t1-t0)

def process_pdf():
  profile = False
  if profile:
    cProfile.run("process_pdf_imp()")
  else:
    process_pdf_imp()

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--getall", dest="getall", default=False, action="store_true")
  parser.add_argument("--test", dest="test", default=False, action="store_true")
  # Save the results to a file
  parser.add_argument("--save", dest="save", default=False, action="store_true")
  # Take the saved file and upload
  parser.add_argument("--upload", dest="upload", default=False, action="store_true")
  parser.add_argument("--showall", dest="showall", default=False, action="store_true")
  parser.add_argument("--findbbox", dest="findbbox", default=False, action="store_true")
  parser.add_argument("--findmeta", dest="findmeta", default=False, action="store_true")
  parser.add_argument("--findschedule", dest="findschedule", default=False, action="store_true")
  parser.add_argument("--findlighting", dest="findlighting", default=False, action="store_true")
  parser.add_argument("--process", dest="process", default=False, action="store_true")
  parser.add_argument("--x0", dest="x0", type=int, required=False)
  parser.add_argument("--y0", dest="y0", type=int, required=False)
  parser.add_argument("--x1", dest="x1", type=int, required=False)
  parser.add_argument("--y1", dest="y1", type=int, required=False)
  parser.add_argument("--page", dest="page", type=int, required=False)
  return parser.parse_args()

def main():
  args = parse_args()
  if args.test:
    test_encode_decode()
  elif args.showall or args.page is not None:
    showall(args.page)
  elif args.x0 is not None and args.y0 is not None and args.x1 is not None and args.y1 is not None:
    # python3 michaelsmithsymbols.py --y0 306 --x0 549 --y1 329 --x1 579
    show_inside(y0=args.y0, x0=args.x0, y1=args.y1, x1=args.x1)
  elif args.getall:
    get_all_symbols(save=args.save)
  elif args.findmeta:
    findmeta()
  elif args.findschedule:
    findschedule()
  elif args.findlighting:
    findlighting()
  elif args.process:
    process_pdf()
  else:
    door_labels_should_match()


if __name__ == "__main__":
  # python3 -m pdfextract.michaelsmithsymbols --process
  main()
