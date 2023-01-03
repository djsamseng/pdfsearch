
import argparse
import typing
import time

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level

import pdfextracter
import pdfdrawer
import pdftkdrawer

import rtree

def extract_window_schedule_test(args):
  load_all = True
  t0 = time.time()
  with np.load("window_schedule_hierarchy.npz", allow_pickle=True) as f:
    window_schedule_elems, width, height = f["elems"], f["width"], f["height"]
    window_schedule_elems: typing.List[pdfminer.layout.LTComponent] = window_schedule_elems
    width = int(width)
    height = int(height)
  t1 = time.time()
  if load_all:
    with np.load("all_pages_hierarchy.npz", allow_pickle=True) as f:
      all_pages_elems = f["elems"]
    page_elems: typing.List[pdfminer.layout.LTComponent] = all_pages_elems[8]
    underlying =  pdfextracter.get_underlying(elems=page_elems)
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    pdftkdrawer.draw_elems(elems=underlying, drawer=drawer)
    drawer.show("First floor construction plan")
    np.savez("first_floor_construction.npz", elems=page_elems, width=width, height=height)
  t2 = time.time()

  print(t1-t0, t2-t1)

def extract_window_key(args):
  with np.load("first_floor_construction.npz", allow_pickle=True) as f:
    page_elems, width, height = f["elems"], f["width"], f["height"]
    page_elems: typing.List[pdfminer.layout.LTComponent] = page_elems
    width = int(width)
    height = int(height)

  underlying =  pdfextracter.get_underlying(elems=page_elems)

  def index_insertion_generator(elems: typing.List[pdfminer.layout.LTComponent]):
    for i, elem in enumerate(elems):
      x0, y0, x1, y1 = elem.bbox
      yield (i, (x0, height-y1, x1, height-y0), i)
  rtree_index = rtree.index.Index(index_insertion_generator(elems=underlying))
  y0, x0 = 1756, 1391
  y1, x1 = 1781, 1418
  found = rtree_index.intersection((x0, y0, x1, y1))
  q01_drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  q01_elems = [underlying[idx] for idx in found]
  pdftkdrawer.draw_elems(elems=q01_elems, drawer=q01_drawer)
  # Each elem is a button. Press to toggle hide/show
  # Press another button to export
  # draw elems with hierarchy and keep hierarchy
  q01_drawer.show("Q01")
  return

  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  pdftkdrawer.draw_elems(elems=underlying, drawer=drawer)
  drawer.show("First floor construction plan")

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--awindows", dest="awindows", default=False, action="store_true")
  return parser.parse_args()

def main():
  args = parse_args()
  if args.awindows:
    extract_window_schedule_test(args)
  else:
    extract_window_key(args)

if __name__ == "__main__":
  main()
