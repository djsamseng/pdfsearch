
import typing
import argparse
import json

import numpy as np
import pdfminer.high_level

import debug_utils
import pdfextracter
import pdfindexer
import pdftkdrawer

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

def get_pdf():
  page_gen = pdfminer.high_level.extract_pages(pdf_file="../plan.pdf", page_numbers=[9])
  pages = list(page_gen)
  page = pages[0]
  width = int(page.width)
  height = int(page.height)
  elem_wrappers = pdfextracter.get_underlying_parent_links(elems=page)
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

  all_symbols: typing.Dict[str, typing.List[pdfextracter.LTJson]] = {
    "notes_circle": notes_circle,
    "window_label": window_label,
    "window_symbol": window_symbol,
    "door_label": door_label,
    "door_symbol": door_symbol,
    "sink_symbol": sink_symbol,
    "toilet_symbol": toilet_symbol,
  }
  if save:
    encoder = pdfextracter.LTJsonEncoder()
    json_string = encoder.encode(all_symbols)
    with open("../lambdacontainer/processpdffunction/symbols_michael_smith.json", "w") as f:
      f.write(json_string)
  else:
    for key, symbol in all_symbols.items():
      drawer = pdftkdrawer.TkDrawer(width=width, height=height)
      drawer.draw_elems(elems=symbol, align_top_left=True)
      drawer.show(key)

def read_symbols_from_json():
  with open("../lambdacontainer/processpdffunction/symbols_michael_smith.json", "r") as f:
    json_string = f.read()
  symbols_dicts = json.loads(json_string)
  symbols: typing.Dict[str, typing.List[pdfextracter.LTJson]] = dict()
  for key, serialized_elems in symbols_dicts.items():
    elems: typing.List[pdfextracter.LTJson] = []
    for serialized_json in serialized_elems:
      elems.append(pdfextracter.LTJson(serialized_json=serialized_json))
    symbols[key] = elems
  return symbols

def find_symbol():
  symbols = read_symbols_from_json()
  elems, width, height = get_pdf()
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  for symbol_key in ["door_label", "window_label"]:
    # notes_circle, door_label fails because of "c" curves
    to_find = symbols[symbol_key][0]
    results_with_text = pdfindexer.find_symbol_with_text(symbol=to_find, indexer=indexer)
    print(len(results_with_text))

    if True:
      drawer_all = pdftkdrawer.TkDrawer(width=width, height=height)
      drawer_all.draw_elems(elems=elems, draw_buttons=False)
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    drawer.draw_elems(elems=results_with_text, draw_buttons=True)
    drawer.show(symbol_key)

def show_inside(y0: float, x0: float, y1: float, x1: float):
  elems, width, height = get_pdf()
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  results = indexer.find_contains(bbox=(x0, y0, x1, y1), y_is_down=True)
  print(results)
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=results, draw_buttons=True)
  drawer.show("All")

def door_labels_should_match():
  y0, x0, y1, x1 = 306, 549, 329, 579
  elems, width, height = get_pdf()
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
  results = indexer.find_contains(bbox=(x0, y0, x1, y1), y_is_down=True)
  symbols = read_symbols_from_json()
  curve = symbols["door_label"][0]
  path = curve.original_path
  curve2 = results[0]
  path2 = curve2.original_path
  print(path)
  print(path2)

  matches = pdfindexer.find_similar_curves(wrapper_to_find=curve, wrappers_to_search=[curve2], max_dist=1)
  print(len(matches))
  return

  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=[curve], align_top_left=True)
  drawer2 = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer2.draw_elems(elems=[curve2], align_top_left=True)

  drawer.show("")


def showall():
  elems, width, height = get_pdf()
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=elems, draw_buttons=False)
  drawer.show("All")

def elems_not_equal(elems: typing.List[pdfextracter.LTJson]):
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
  encoder = pdfextracter.LTJsonEncoder()
  json_string = encoder.encode(elem_wrappers)

  elem_dicts = json.loads(json_string)
  np.testing.assert_allclose(len(elem_dicts), len(elem_wrappers))
  elems = [pdfextracter.LTJson(serialized_json=elem) for elem in elem_dicts]
  for idx in range(len(elems)):
    if elems[idx] != elem_wrappers[idx]:
      print("Not equal:", elems[idx], elem_wrappers[idx])
      return

  np.testing.assert_array_equal(elems, elem_wrappers) # type: ignore
  assert elems == elem_wrappers
  if True:
    print("Checking no equal elements out of {0}".format(len(elems)))
    elems_not_equal(elems=elems)

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
  parser.add_argument("--x0", dest="x0", type=int, required=False)
  parser.add_argument("--y0", dest="y0", type=int, required=False)
  parser.add_argument("--x1", dest="x1", type=int, required=False)
  parser.add_argument("--y1", dest="y1", type=int, required=False)
  return parser.parse_args()

def main():
  args = parse_args()
  if args.test:
    test_encode_decode()
  elif args.find:
    find_symbol()
  elif args.showall:
    showall()
  elif args.x0 is not None and args.y0 is not None and args.x1 is not None and args.y1 is not None:
    # python3 michaelsmithsymbols.py --y0 306 --x0 549 --y1 329 --x1 579
    show_inside(y0=args.y0, x0=args.x0, y1=args.y1, x1=args.x1)
  elif args.getall:
    get_all_symbols(save=args.save)
  else:
    door_labels_should_match()


if __name__ == "__main__":
  main()