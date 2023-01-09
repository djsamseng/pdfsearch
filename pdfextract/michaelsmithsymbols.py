
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

  all_symbols = {
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
    for idx1 in range(len(elems)):
      for idx2 in range(len(elems)):
        if idx1 != idx2:
          assert elems[idx1] != elems[idx2], "idx1={0} idx2={1} elem1={2} elem2={3}".format(idx1, idx2, elems[idx1], elems[idx2])

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--test", dest="test", default=False, action="store_true")
  # Save the results to a file
  parser.add_argument("--save", dest="save", default=False, action="store_true")
  # Take the saved file and upload
  parser.add_argument("--upload", dest="upload", default=False, action="store_true")
  return parser.parse_args()

def main():
  args = parse_args()
  if args.test:
    test_encode_decode()
  else:
    get_all_symbols(save=args.save)

if __name__ == "__main__":
  main()