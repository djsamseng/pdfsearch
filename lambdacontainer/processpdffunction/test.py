

import collections
import cProfile
import enum
import dataclasses
import heapq
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

from pdfextract import debug_utils, path_utils, pdftypes
from pdfextract import pdfelemtransforms
from pdfextract import pdfextracter
from pdfextract import pdfindexer, symbol_indexer, leafgrid
from pdfextract import pdftkdrawer, classifier_drawer
from pdfextract import votesearch
from pdfextract import dataprovider, pdfprocessor
from pdfextract.ltjson import LTJson, LTJsonEncoder, ScheduleTypes
from pdfextract.pdftypes import Bbox, ClassificationNode, ClassificationType

def get_pdf(
  which:int = 0,
  page_number:typing.Union[int, None]=None,
  overwrite: bool=False,
):
  filename = "{0}-{1}.pickle".format(which, page_number)
  if not overwrite:
    if os.path.isfile(filename):
      with open(filename, "rb") as f:
        elems, celems, width, height = pickle.load(f)
      return elems, celems, width, height
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

  with open(filename, "wb") as f:
    pickle.dump((
      elem_wrappers,
      celems,
      width,
      height,
    ), f)
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
) -> typing.List[
  typing.List[
    ClassificationNode
  ]
]:
  layers: typing.List[
    typing.List[
      ClassificationNode
    ]
  ] = [[], []]
  # We don't want to create parents because
  # we activate children in order to find similar parents
  create_parents = False
  for child in elems:
    if isinstance(child, pdfminer.layout.LTContainer):
      assert False, "pdfminer/layout.py line 959 def analyze to return early"
    elif isinstance(child, pdfminer.layout.LTChar):
      layers[0].append(
        ClassificationNode(
          layer_idx=0,
          in_layer_idx=len(layers[0]),
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
        if child.linewidth > 0:
          lines = path_utils.path_to_lines(path=child.original_path)
          parent_idx = len(layers[1])
          idxes: typing.List[int] = []
          for line in lines:
            x0, y0, x1, y1 = line
            child_idx = len(layers[0])
            idxes.append(child_idx)
            node = ClassificationNode(
              layer_idx=0,
              in_layer_idx=child_idx,
              elem=child,
              bbox=(x0, y0, x1, y1),
              line=line,
              text=None,
              child_idxes=[],
            )
            if create_parents:
              node.parent_idxes = [parent_idx]
            layers[0].append(node)
          if create_parents:
            parent_node = ClassificationNode(
              layer_idx=1,
              in_layer_idx=len(layers[1]),
              elem=None,
              bbox=child.bbox,
              line=None,
              text=None,
              child_idxes=idxes
            )
            layers[1].append(parent_node)

    elif isinstance(child, pdfminer.layout.LTFigure):
      pass
    elif isinstance(child, pdfminer.layout.LTImage):
      pass
    else:
      print("Unhandled elem:", child)
  return layers

def grid_test():
  import numpy as np
  _, layers, width, height = get_pdf(which=0, page_number=9)
  celems = layers[0]
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
  _, layers, width, height = get_pdf(which=0, page_number=9)
  celems = layers[0]
  step_size = 5
  leaf_grid = leafgrid.LeafGrid(celems=celems, step_size=step_size, width=width, height=height)
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=celems, draw_buttons=False)
  drawer.show("ClassifierDrawer")

def get_rounded_bbox(bbox: Bbox):
  return (
    math.floor(bbox[0]),
    math.floor(bbox[1]),
    math.ceil(bbox[2]),
    math.ceil(bbox[3]),
  )

@dataclasses.dataclass(order=True)
class QTextNode():
  score: float = dataclasses.field(compare=True)
  def __init__(
    self,
    text:str,
    bbox:Bbox,
    score: float=0,
  ) -> None:
    self.text = text
    self.bbox = bbox
    self.score = score

  def __repr__(self) -> str:
    return self.__str__()

  def __str__(self) -> str:
    return json.dumps(self.as_dict())

  def as_dict(self):
    out: typing.Dict[str, typing.Any] = dict()
    for key in self.__dict__.keys():
      if not key.startswith("_{0}__".format(self.__class__.__name__)):
        out[key] = self.__dict__[key]
    return out

def get_distance_between(a: QTextNode, b: QTextNode, vert: bool=False):
  if vert:
    idx0 = 1
    idx1 = 3
  else:
    idx0 = 0
    idx1 = 2
  if a.bbox[idx0] >= b.bbox[idx1]:
    return a.bbox[idx0] - b.bbox[idx1]
  elif b.bbox[idx0] >= a.bbox[idx1]:
    return b.bbox[idx0] - a.bbox[idx1]
  else:
    return 0

def get_length(a: QTextNode, vert: bool=False):
  if vert:
    idx0 = 1
    idx1 = 3
  else:
    idx0 = 0
    idx1 = 2
  return a.bbox[idx1] - a.bbox[idx0]

def get_overlaps(a: QTextNode, b:QTextNode, vert: bool=False):
  if vert:
    idx0 = 1
    idx1 = 3
  else:
    idx0 = 0
    idx1 = 2
  if a.bbox[idx0] + 0.1 < b.bbox[idx1] and a.bbox[idx1] - 0.1 > b.bbox[idx0]:
    return True
  return False

def make_joined_q_text_nodes(a: QTextNode, b: QTextNode, base_score: float=1):
  horiz_distance = get_distance_between(a, b, vert=False)
  vert_distance = get_distance_between(a, b, vert=True)
  a_width = get_length(a, vert=False)
  b_width = get_length(b, vert=False)

  if vert_distance > 0:
    score = 0.001
  else:
    score = 1 / (horiz_distance + 1)
  if a.bbox[0] < b.bbox[0]:
    left_node = a
    right_node = b
  else:
    left_node = b
    right_node = a
  if horiz_distance > max(a_width, b_width) * 0.5:
    space_str = " "
  else:
    space_str = ""
  joined_text = left_node.text + space_str + right_node.text
  joined_bbox = (
    min(a.bbox[0], b.bbox[0]),
    min(a.bbox[1], b.bbox[1]),
    max(a.bbox[2], b.bbox[2]),
    max(a.bbox[3], b.bbox[3]),
  )
  score *= base_score
  score = 1 - score
  if get_overlaps(a, b, vert=False):
    score = 1 # Last
  return QTextNode(text=joined_text, bbox=joined_bbox, score=score)

def joinword_test():
  _, layers, width, height = get_pdf(which=0, page_number=2)
  celems = layers[0]
  char_elems = [
    celems[idx] for idx in [
      1543, 1544, 1545, 1546, 1547, 1548, 1549, 1550, 1551, 1552, 1553, 1554, 1555
    ]
  ]

  char_elems = [QTextNode(text=c.text or "", bbox=c.bbox) for c in char_elems]
  join_q: typing.List[QTextNode] = []
  for elem in char_elems:
    heapq.heappush(join_q, elem)
  while len(join_q) >= 2:
    new_nodes: typing.List[QTextNode] = []
    for idxa, node_a in enumerate(join_q):
      for idxb, node_b in enumerate(join_q):

        if idxa != idxb:
          new_node = make_joined_q_text_nodes(node_a, node_b, base_score=node_a.score * node_b.score)
          new_nodes.append(new_node)
          if node_a.text == "DO" and node_b.text == "OR":
            print("HERE!", node_a, node_b)
            print(new_node)
            return
    for node in new_nodes:
      heapq.heappush(join_q, node)

  print("Num left:", len(join_q))
  print(join_q)

  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=celems, draw_buttons=False)
  drawer.show("ClassifierDrawer")

def what_is_this_test():
  _, layers, width, height = get_pdf(which=0, page_number=2)
  celems = layers[0]
  # Instance of "A" <-> Symbol "A"
  #      |                     |
  # Instance of "Alpha" -  Symbol "Alpha"
  step_size = 5
  leaf_grid = leafgrid.LeafGrid(celems=celems, step_size=step_size, width=width, height=height)
  bbox = (0, 0, width, height)
  first_text = leaf_grid.first_elem(bbox=bbox, text_only=True)
  print("1:", first_text)
  if first_text is None:
    return
  restrict_idxes = {
    first_text.node_id: True,
  }
  x0, y0, x1, y1 = first_text.node.bbox
  nodes_used: typing.List[leafgrid.GridNode] = [first_text]
  for next_grid_node in leaf_grid.next_elem_for_coords(
    x0=x0, y0=y0, x1=x1, y1=y1,
    direction=leafgrid.Direction.RIGHT,
    restrict_idxes=restrict_idxes
  ):
    if next_grid_node.node.text is not None:
      print("2:", next_grid_node.node.text)
    nodes_used.append(next_grid_node)
    x0 = next_grid_node.node.bbox[0]
    restrict_idxes[next_grid_node.node_id] = True
    next_grid_node = leaf_grid.next_elem_for_coords(
      x0=x0, y0=y0, x1=x1, y1=y1,
      direction=leafgrid.Direction.RIGHT,
      restrict_idxes=restrict_idxes
    )

  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  # draw = [n.node for n in nodes_used]
  drawer.draw_elems(elems=celems, align_top_left=False)
  drawer.show("What")

def preload_activation_map(celems: typing.List[ClassificationNode]):
  results: typing.Dict[ClassificationType, typing.DefaultDict[typing.Any, int]] = {}
  # Ranges of slopes -> buckets -> map buckets to elems
  for classification_type in ClassificationType:
    results[classification_type] = collections.defaultdict(int) # number of times an activation score occurs
  for elem in celems:
    classifications = elem.get_classifications()
    for ctype, value in classifications:
      results[ctype][value] += 1
  # Buckets of [ [0 < slope < 0.1], [0.1 < slope < 0.2], ...] where each bucket has about the same number of elements
  # This is just for efficiency of finding close neighbors
  # Then we can merge the set of results over multiple types
  # Create a parent classification node with multiple lines that are physically close to each other
  #   Add pointers from the children to the parent
  # When matching, we match the child nodes (position independent)
  # However the matched child nodes reactivate the parent node thus activating the memory
  # Text is a superset where words and sentences form
  return results

def shapememory_test():
  _, layers, width, height = get_pdf(which=1, page_number=1)
  celems = layers[0]
  window_label_with_pointer_line_idxes = [
    6448, 6449, 6450, 6451, 6452, 6453, 6454, 6455, 6456, 6457
  ]
  window_label_with_pointer_line = [
    celems[idx] for idx in window_label_with_pointer_line_idxes
  ]
  window_labels = [*window_label_with_pointer_line[:6], *window_label_with_pointer_line[7:]]
  shape_manager = symbol_indexer.ShapeManager(leaf_layer=layers[0])
  shape_manager.add_shape(
    shape_id="window_label",
    lines=[l.line for l in window_labels if l.line is not None]
  )

  print("Layers before:", [len(l) for l in layers])
  nodes_used = shape_manager.activate_layers()
  print("Layers after:", [len(l) for l in layers])
  nodes_used_b = shape_manager.activate_layers()
  assert len(nodes_used_b) == 0, "Second activation got nodes: {0}".format(nodes_used_b)
  print("Layers after:", [len(l) for l in layers])
  # TODO: use children_idxes of shape_manager.results to draw recursively

  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=nodes_used)
  drawer.show("C")
  # Draw elems that activated a symbol enough

def sqft_test():
  _, layers, width, height = get_pdf(which=1, page_number=1)
  celems = layers[0]
  window_schedule_part_idxes = [
    17102, 17105, 17107, 17108, 17120, 17122, 17131, 17132, 17133, 17134, 17135,
    17136, 17137, 17138, 17139, 17140, 17141, 17142, 17143, 17144, 17145, 17146,
    17147, 17148, 17149, 17150, 17151, 17152, 17153, 17154, 17204, 17205, 17206,
    17207, 17208, 17209, 17210, 17211, 17212, 17213, 17214, 17215, 17216, 17217,
    17218, 17219, 18078, 18079, 18080, 18081, 18082, 18083, 18084, 18085, 18086,
    18087, 18088, 18089, 18090,
    17103, 17104
  ]
  celems = [ celems[idx] for idx in window_schedule_part_idxes ]

  manager = symbol_indexer.ShapeManager(leaf_layer=celems)
  manager.activate_layers()

  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=celems, align_top_left=True)
  drawer.show("C")
  x_start, y_start = 1022, 1002
  wall_x0, wall_y0, wall_x1, wall_y1 = 886, 889, 1129, 1142
  wall_idxes = [7835, 7837, 8069, 9224]
  # Can't look so narrowly. Luckily with lines we can look more broadly
  # See what lines are connected. Start with path following but protected by the whole context
  # Ex: I don't want to go down that line yet because I saw a horizontal wall nearby that cuts it off
  # 1. See the outside by whitespace
  # 2. Classify the reference lines showing distances by the text
  # 3. Thic


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--profile", dest="profile", default=False, action="store_true")
  parser.add_argument("--vote", dest="vote", default=False, action="store_true")
  parser.add_argument("--grid", dest="grid", default=False, action="store_true")
  parser.add_argument("--leafgrid", dest="leafgrid", default=False, action="store_true")
  parser.add_argument("--joinword", dest="joinword", default=False, action="store_true")
  parser.add_argument("--what", dest="what", default=False, action="store_true") # TODO: continue to form words
  parser.add_argument("--shapememory", dest="shapememory", default=False, action="store_true")
  parser.add_argument("--sqft", dest="sqft", default=False, action="store_true")
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
  elif args.joinword:
    func = joinword_test
  elif args.what:
    func = what_is_this_test
  elif args.shapememory:
    func = shapememory_test
  elif args.sqft:
    func = sqft_test
  if func:
    if args.profile:
      cProfile.run("{0}()".format(func.__name__))
    else:
      func()

if __name__ == "__main__":
  main()
