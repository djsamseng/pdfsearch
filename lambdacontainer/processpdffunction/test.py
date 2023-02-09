

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

import pdfminer.high_level, pdfminer.utils, pdfminer.layout

from pdfextract import debug_utils, path_utils
from pdfextract import pdfelemtransforms
from pdfextract import pdfextracter
from pdfextract import pdfindexer
from pdfextract import pdftkdrawer
from pdfextract import votesearch
from pdfextract import dataprovider, pdfprocessor
from pdfextract.ltjson import LTJson, LTJsonEncoder, BboxType, ScheduleTypes

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

def get_curve_size(elem: LTJson):
  if elem.original_path is not None:
    curves = [ c for c in elem.original_path if c[0] == "c"]
    if len(curves) > 0:
      return elem.width * elem.height, elem
  return 0, elem

def vote_test():
  #      1    0.038    0.038   12.150   12.150 test.py:46(vote_test)
  #      2    0.000    0.000    4.984    2.492 high_level.py:180(extract_pages)
  #  14464    0.009    0.000    5.081    0.000 pdfindexer.py:103(find_intersection)
  #  14464    0.014    0.000    1.022    0.000 index.py:750(intersection)
  # 708517    0.419    0.000    3.840    0.000 index.py:911(_get_objects)
  elems, width, height = get_pdf(which=0, page_number=9)

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
  return
  # Curves are decomposed into lots of small lines
  draw_elems: typing.List[LTJson] = to_index

  drawer = pdftkdrawer.TkDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=draw_elems, align_top_left=True, draw_buttons=False)
  drawer.show("Vote test")

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--profile", dest="profile", default=False, action="store_true")
  parser.add_argument("--vote", dest="vote", default=False, action="store_true")
  return parser.parse_args()

def main():
  args = parse_args()
  func = None
  if args.vote:
    func = vote_test

  if func:
    if args.profile:
      cProfile.run("{0}()".format(func.__name__))
    else:
      func()

if __name__ == "__main__":
  main()
