
import argparse
import typing
import time

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level

import pdfextracter
import pdfdrawer
import pdftkdrawer

import scipy.spatial
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
  show_ui = True
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
  q01_elems = [underlying[idx] for idx in found]
  q01_search_elems = q01_elems[2:6]
  search_elem = q01_search_elems[0]
  # all elements with same len(original_path) and similar shaped bbox
  # then break the original path into individual lines
  # then compare the lines
  # this will be a bit more difficult for bezier "c" paths
  # divide elements into len(original_path)
  # divide elements into bbox sizes/shapes

  elem_shapes = [[elem.width, elem.height] for elem in underlying]
  kdtree_index = scipy.spatial.KDTree(data=elem_shapes)
  search_elem_shape = [search_elem.width, search_elem.height]
  neighbor_idxes = kdtree_index.query_ball_point(x=search_elem_shape, r=1)
  neighbor_elems = [underlying[idx] for idx in neighbor_idxes]
  draw_elems = []
  for elem in neighbor_elems:
    x0, y0, x1, y1 = elem.bbox
    content_bbox = (x0, height-y1, x1, height-y0)
    neighbor_content_idxes = rtree_index.contains(content_bbox)
    neighbor_contents = [underlying[idx] for idx in neighbor_content_idxes]
    char_elems = [ n for n in neighbor_contents if isinstance(n, pdfminer.layout.LTChar)]
    char_elems.sort(key=lambda elem: elem.x0)
    print("".join([c.get_text() for c in char_elems]))
    draw_elems.extend(char_elems)
  draw_elems.extend(neighbor_elems)

  if show_ui:
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    pdftkdrawer.draw_elems(elems=draw_elems, drawer=drawer)

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
