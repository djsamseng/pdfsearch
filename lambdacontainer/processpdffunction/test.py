

import collections
import cProfile
import functools
import os
import math
import random
import pickle
import time
import typing
import argparse
import json
import gzip
import re

import pdfminer.high_level, pdfminer.utils, pdfminer.layout
import rtree

from pdfextract import debug_utils, path_utils
from pdfextract import pdfelemtransforms
from pdfextract import pdfextracter
from pdfextract import pdfindexer
from pdfextract import pdftkdrawer, classifier_drawer
from pdfextract import votesearch
from pdfextract import dataprovider, pdfprocessor
from pdfextract.ltjson import LTJson, LTJsonEncoder, ScheduleTypes
from pdfextract.pdftypes import Bbox, ClassificationNode

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
  elems = list(page)
  elem_wrappers = pdfelemtransforms.get_underlying_parent_links(elems=elems)
  celems = get_classification_nodes(elems=elems)
  return elem_wrappers, celems, width, height

def get_curve_size(elem: LTJson):
  if elem.original_path is not None:
    curves = [ c for c in elem.original_path if c[0] == "c"]
    if len(curves) > 0:
      return elem.width * elem.height, elem
  return 0, elem

def sign(val: float) -> int:
  if val == 0:
    return 0
  elif val < 0:
    return -1
  return 1



class PdfLeafIndexer:
  def __init__(
    self,
    elems: typing.List[ClassificationNode]
  ) -> None:
    self.elems = elems
    def insertion_generator(
      elems: typing.List[ClassificationNode],
    ):
      for elem_idx, elem in enumerate(elems):
        if elem.text is not None:
          yield (elem_idx, elem.bbox, None)
        elif elem.line is not None:
          yield (elem_idx, elem.bbox, None)
    self.find_by_position_rtree = rtree.index.Index(insertion_generator(elems=elems))

  def find_intersection(
    self,
    bbox: Bbox,
  ) -> typing.List[ClassificationNode]:
    idxes = self.find_by_position_rtree.intersection(bbox, objects=False)
    results = [ self.elems[idx] for idx in idxes ] #pylint: disable=not-an-iterable
    return results


def get_classification_nodes(
  elems: typing.Iterable[pdfminer.layout.LTComponent]
) -> typing.List[ClassificationNode]:
  out: typing.List[ClassificationNode] = []
  for child in elems:
    if isinstance(child, pdfminer.layout.LTContainer):
      out.extend(
        get_classification_nodes(
          elems=typing.cast(typing.Iterable[pdfminer.layout.LTComponent], child)
        )
      )
    elif isinstance(child, pdfminer.layout.LTChar):
      out.append(
        ClassificationNode(
          elem=child,
          bbox=child.bbox,
          line=None,
          text=child.get_text(),
          child_idxes=[]
        )
      )
    elif isinstance(child, pdfminer.layout.LTAnno):
      pass
    elif isinstance(child, pdfminer.layout.LTCurve):
      if child.original_path is not None:
        lines = path_utils.path_to_lines(path=child.original_path)
        idxes: typing.List[int] = []
        line_nodes: typing.List[ClassificationNode] = []
        for line in lines:
          (x0, y0), (x1, y1) = line
          idxes.append(len(out))
          line_nodes.append(
            ClassificationNode(
              elem=child,
              bbox=(x0, y0, x1, y1),
              line=line,
              text=None,
              child_idxes=[]
            )
          )
        parent_idx = len(out) + len(line_nodes)
        for node in line_nodes:
          node.parent_idxes = [parent_idx]
        out.extend(line_nodes)
        out.append(
          ClassificationNode(
            elem=None,
            bbox=child.bbox,
            line=None,
            text=None,
            child_idxes=idxes
          )
        )

    elif isinstance(child, pdfminer.layout.LTFigure):
      pass
    elif isinstance(child, pdfminer.layout.LTImage):
      pass
    else:
      print("Unhandled elem:", child)
  return out

def grid_test():
  import numpy as np
  _, celems, width, height = get_pdf(which=0, page_number=9)
  leaf_indexer = PdfLeafIndexer(elems=celems)
  GridType = typing.List[typing.List[typing.List[ClassificationNode]]]
  grid_indexer: GridType = [[ [] for _ in range(width)] for _ in range(height)] # y, x
  np_grid = np.zeros(shape=(height, width), dtype=object)
  for y in range(height):
    for x in range(width):
      np_grid[y, x] = []
  for elem in celems:
    x0, y0, _, _ = elem.bbox
    grid_indexer[round(y0)][round(x0)].append(elem)
    np_grid[round(y0), round(x0)].append(elem)

  def query_grid(grid_indexer: GridType, x0: int, y0: int, x1: int, y1: int):
    results = [wgrid[x0: x1] for wgrid in grid_indexer[y0:y1]]
    return results
  def query_np(np_grid: typing.Any, x0: int, y0: int, x1: int, y1: int):
    results = np_grid[y0:y1, x0:x1]
    return results
  def concat_grid_results(results: GridType):
    out: typing.List[ClassificationNode] = []
    for row_ary in results:
      for cell_results in row_ary:
        out.extend(cell_results)
    return out
  def query_leaf(leaf_indexer: PdfLeafIndexer, x0: int, y0: int, x1: int, y1: int):
    results = leaf_indexer.find_intersection(bbox=(x0, y0, x1, y1))
    return results

  for _ in range(1000):
    x0 = 700 + random.randint(0, 10)
    x1 = 790 + random.randint(0, 10)
    y0 = 450 + random.randint(0, 10)
    y1 = 512 + random.randint(0, 10)
    grid_results = query_grid(grid_indexer, x0, y0, x1, y1)
    leaf_results = query_leaf(leaf_indexer, x0, y0, x1, y1)
    np_results = query_np(np_grid, x0, y0, x1, y1)
    grid_concat_results = concat_grid_results(grid_results)
    np_concat_results = concat_grid_results(np_results)
    print(len(grid_concat_results), len(leaf_results), len(np_concat_results))
  # 1000    0.001    0.000    0.018    0.000 test.py:179(query_grid)
  # 1000    0.001    0.000    0.001    0.000 test.py:182(query_np)
  # 2000    0.688    0.000    1.006    0.001 test.py:185(concat_grid_results)
  # 1000    0.001    0.000    0.057    0.000 test.py:191(query_leaf)



def vote_test():
  #      1    0.038    0.038   12.150   12.150 test.py:46(vote_test)
  #      2    0.000    0.000    4.984    2.492 high_level.py:180(extract_pages)
  #  14464    0.009    0.000    5.081    0.000 pdfindexer.py:103(find_intersection)
  #  14464    0.014    0.000    1.022    0.000 index.py:750(intersection)
  # 708517    0.419    0.000    3.840    0.000 index.py:911(_get_objects)
  elems, celems, width, height = get_pdf(which=0, page_number=9)

  curve_sizes = [get_curve_size(elem) for elem in elems]
  largest = max(elems, key=lambda x: x.width*x.height)
  max_curve = max(curve_sizes, key=lambda x:x[0])

  to_index = [max_curve[1], largest]
  # TODO: sort LineIndexer so that we can walk from a given x,y
  indexer = pdfindexer.PdfIndexer(wrappers=elems, page_height=height, page_width=width)
  for elem in elems:
    if elem.text is not None:
      radius = max(elem.width, elem.height) * 2
      x0, y0, x1, y1 = elem.bbox
      search_box = (
        x0 - radius,
        y0 - radius,
        x1 + radius,
        y1 + radius,
      )
      nearby = indexer.find_intersection(search_box)
      if len(nearby) == 0:
        print("Should not be true")
      elif len(nearby) == 1:
        print("Only found self")
  # I have a set of things to search for
  # I look from left to right, top down and start joining things together
  # Classify groups/areas
  # A window will have a window symbol but also be in the context of a window
  leaf_indexer = PdfLeafIndexer(elems=celems)


  return
  # Curves are decomposed into lots of small lines
  draw_elems: typing.List[LTJson] = to_index

  drawer = pdftkdrawer.TkDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=draw_elems, align_top_left=True, draw_buttons=False)
  drawer.show("Vote test")

def leafgrid_test():
  _, celems, width, height = get_pdf(which=0, page_number=9)
  step_size = 5
  def coord_for(x: float) -> int:
    return math.floor(x / step_size)
  GridType = typing.List[typing.List[typing.List[int]]]
  grid: GridType = [[[] for _ in range(coord_for(width)+1)] for _ in range(coord_for(height)+1)]
  # 1    0.227    0.227    0.331    0.331 test.py:267(insert_elems) step size 1
  # 1    0.094    0.094    0.159    0.159 test.py:266(insert_elems) step size 5
  def insert_elems(grid: GridType, celems: typing.List[ClassificationNode]):
    for idx, elem in enumerate(celems):
      if elem.text is not None:
        x0, y0, x1, y1 = elem.bbox
        x0, y0, x1, y1 = coord_for(x0), coord_for(y0), coord_for(x1), coord_for(y1)
        for y in range(y0, y1+1):
          for x in range(x0, x1+1):
            grid[y][x].append(idx)
      elif elem.line is not None:
        (x0, y0), (x1, y1) = elem.line
        x0, y0, x1, y1 = coord_for(x0), coord_for(y0), coord_for(x1), coord_for(y1)
        for y in range(y0, y1+1):
          for x in range(x0, x1+1):
            grid[y][x].append(idx)
  insert_elems(grid=grid, celems=celems)
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=celems, draw_buttons=False)
  drawer.show("ClassifierDrawer")


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--profile", dest="profile", default=False, action="store_true")
  parser.add_argument("--vote", dest="vote", default=False, action="store_true")
  parser.add_argument("--grid", dest="grid", default=False, action="store_true")
  parser.add_argument("--leafgrid", dest="leafgrid", default=False, action="store_true")
  return parser.parse_args()

def main():
  args = parse_args()
  func = None
  if args.vote:
    func = vote_test
  elif args.grid:
    func = grid_test
  elif args.leafgrid:
    func = leafgrid_test
  if func:
    if args.profile:
      cProfile.run("{0}()".format(func.__name__))
    else:
      func()

if __name__ == "__main__":
  main()
