
import argparse
import typing

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level

import pdfdrawer
import pdfextracter

def extract_window_schedule_and_save():
  page_gen = pdfminer.high_level.extract_pages(pdf_file="../plan.pdf", page_numbers=[3-1])
  page = next(iter(page_gen))

  drawer = pdfdrawer.FitzDraw(width=page.width, height=page.height)
  elems = pdfextracter.get_underlying(page=page)

  y0, x0 = 918, 958
  y1, x1 = 2100, 1865
  bbox = (x0, page.height-y1, x1, page.height-y0)
  found_elems = pdfextracter.filter_contains_bbox(elems=elems, bbox=bbox)

  pdfdrawer.draw_elems(elems=found_elems, drawer=drawer)
  drawer.show("Window Schedule")
  pdfdrawer.waitKey(0)
  np.savez("window_schedule.npz", elems=found_elems, width=page.width, height=page.height)

def extract_window_schedule_with_hierarchy_and_save():
  page_gen = pdfminer.high_level.extract_pages(pdf_file="../plan.pdf", page_numbers=[3-1])
  page = next(iter(page_gen))

  y0, x0 = 918, 958
  y1, x1 = 2100, 1865
  bbox = (x0, page.height-y1, x1, page.height-y0)
  found_elems = pdfextracter.filter_contains_bbox_hierarchical(elems=page, bbox=bbox)
  print(found_elems)

  np.savez("window_schedule_hierarchy.npz", elems=found_elems, width=page.width, height=page.height)

def extract_underlying_all_pages_and_save():
  page_gen = pdfminer.high_level.extract_pages(pdf_file="../plan.pdf")
  page_underlying = []
  for page in page_gen:
    elems = pdfextracter.get_underlying(page=page)
    page_underlying.append(elems)
  np.savez("all_pages_underlying.npz", width=page.width, height=page.height)

def extract_all_pages_with_hierarchy_and_save():
  page_gen = pdfminer.high_level.extract_pages(pdf_file="../plan.pdf")
  page_underlying = []
  for page in page_gen:
    elems = list(page)
    page_underlying.append(elems)
  np.savez("all_pages_hierarchy.npz", width=page.width, height=page.height)

def get_awindows_key(window_schedule_elems: typing.Iterable[pdfminer.layout.LTComponent], page_width: int, page_height: int):
  y0, x0 = 1027, 971
  y1, x1 = 1043, 994
  bbox = (x0, page_height-y1, x1, page_height-y0)
  key_elems = pdfextracter.filter_contains_bbox_hierarchical(elems=window_schedule_elems, bbox=bbox)
  return key_elems

def print_elem_tree(elems, depth=0):
  for elem in elems:
    print("".ljust(depth, "-"), elem)
    if isinstance(elem, pdfminer.layout.LTContainer):
      print_elem_tree(elems=elem, depth=depth+1)

def extract_window_schedule_test():
  with np.load("window_schedule_hierarchy.npz", allow_pickle=True) as f:
    window_schedule_elems, width, height = f["elems"], f["width"], f["height"]
    window_schedule_elems: pdfextracter.ElemListType = window_schedule_elems
    width = int(width)
    height = int(height)

  drawer = pdfdrawer.PygletDraw(width=width, height=height) #pdfdrawer.FitzDraw(width=width, height=height)
  awindows_key = get_awindows_key(window_schedule_elems=window_schedule_elems, page_width=width, page_height=height)
  #print_elem_tree(elems=window_schedule_elems)
  print("========")
  print_elem_tree(elems=awindows_key)
  underlying = pdfextracter.get_underlying(window_schedule_elems)
  pdfdrawer.draw_elems(elems=underlying, drawer=drawer)
  drawer.show("A Windows Key")
  pdfdrawer.waitKey(0)

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--awindows", dest="awindows", default=False, action="store_true")
  return parser.parse_args()

def main():
  args = parse_args()
  if args.awindows:
    extract_window_schedule_test()
  else:
    extract_window_schedule_test()

if __name__ == "__main__":
  main()
