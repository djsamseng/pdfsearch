

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
from pdfextract.pdftypes import Bbox, ClassificationNode, ClassificationType, LabelType

def get_pdf(
  which:int = 0,
  page_number:typing.Union[int, None]=None,
  overwrite: bool=False,
) -> typing.Tuple[
  typing.List[LTJson],
  typing.List[typing.List[pdftypes.ClassificationNode]],
  int,
  int
]:
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


def get_window_schedule_pdf():
  window_schedule_idxes = [
    17102, 17103, 17105, 17106, 17107, 17108, 17109, 17110, 17111, 17112, 17113,
    17114, 17120, 17122, 17123, 17124, 17125, 17126, 17127, 17128, 17129, 17130,
    17131, 17132, 17133, 17134, 17135, 17136, 17137, 17138, 17139, 17140, 17141,
    17142, 17143, 17144, 17145, 17146, 17147, 17148, 17149, 17150, 17151, 17152,
    17153, 17154, 17155, 17156, 17157, 17158, 17159, 17160, 17161, 17162, 17163,
    17164, 17165, 17166, 17167, 17168, 17169, 17170, 17171, 17172, 17173, 17174,
    17175, 17176, 17177, 17178, 17179, 17180, 17181, 17182, 17183, 17184, 17185,
    17186, 17187, 17188, 17189, 17190, 17191, 17192, 17193, 17194, 17195, 17196,
    17197, 17198, 17199, 17200, 17201, 17202, 17203, 17204, 17205, 17206, 17207,
    17208, 17209, 17210, 17211, 17212, 17213, 17214, 17215, 17216, 17217, 17218,
    17219, 17220, 17221, 17222, 17223, 17224, 17225, 17226, 17227, 17228, 17229,
    17230, 17231, 17232, 17233, 17234, 17235, 17236, 17237, 17238, 17239, 17240,
    17241, 17242, 17243, 17244, 17245, 17246, 17247, 17248, 17249, 17250, 17251,
    17252, 17253, 17254, 17255, 17256, 17257, 17258, 17259, 17260, 17261, 17262,
    17263, 17264, 17265, 17266, 17267, 17268, 17269, 17270, 17271, 17272, 17273,
    17274, 17275, 17276, 17277, 17278, 17279, 17280, 17281, 17282, 17283, 17284,
    18078, 18079, 18080, 18081, 18082, 18083, 18084, 18085, 18086, 18087, 18088,
    18089, 18090, 18244, 18245, 18246, 18247, 18248, 18249, 18250, 18251, 18252,
    18253, 18254, 18255, 18256, 18257, 18258, 18259, 18260, 18261, 18262, 18263,
    18264, 18265, 18266, 18267, 18268, 18269, 18270, 18271, 18272, 18273, 18274,
    18275, 18276, 18277, 18278, 18279, 18280, 18281, 18282, 18283, 18284, 18285,
    18286, 18287, 18288, 18289, 18290, 18291, 18292, 18293, 18294, 18295, 18296,
    18297, 18298, 18299, 18300, 18301, 18302, 18303, 18304, 18305, 18306, 18307,
    18308, 18309, 18310, 18311, 18312, 18313, 18314, 18315, 18316, 18317, 18318,
    18319, 18320, 18321, 18322, 18323, 18324, 18325, 18326, 18327, 18328, 18329,
    18330, 18331, 18332, 18333, 18334, 18335, 18336, 18337, 18338, 18339, 18340,
    18341, 18342, 18343, 18344, 18345, 18346, 18347, 18348, 18349, 18350, 18351,
    18352, 18353, 18354, 18355, 18356, 18357, 18358, 18359, 18360, 18361, 18362,
    18363, 18364, 18365, 18366, 18367, 18368, 18369, 18370, 18371, 18372, 18373,
    18374, 18375, 18376, 18377, 18378, 18379, 18380, 18381, 18382, 18383, 18384,
    18385, 18386, 18387, 18388, 18389, 18390, 18391, 18392, 18393, 18394, 18395,
    18396, 18397, 18398, 18399, 18400, 18401, 18402, 18403, 18404, 18405, 18406,
    18407, 18408, 18409, 18410, 18411, 18412, 18413, 18414, 18415, 18416, 18417,
    18418, 18419, 18420, 18421, 18422, 18423, 18424, 18425, 18426, 18427, 18428,
    18429, 18430, 18431, 18432, 18433, 18434, 18435, 18436, 18437, 18438, 18439,
    18440, 18441, 18442, 18443, 18444, 18445, 18446, 18447, 18448, 18449, 18450,
    18451, 18452, 18453, 18454, 18455, 18456, 18457, 18458, 18459, 18460, 18461,
    18462, 18463, 18464, 18465, 18466, 18467, 18468, 18469, 18470, 18471, 18472,
    18473, 18474, 18475, 18476, 18477, 18478, 18479, 18480, 18481, 18482, 18483,
    18484, 18485, 18486, 18487, 18488, 18489, 18490, 18491, 18492, 18493, 18494,
    18495, 18496, 18497, 18498, 18499, 18500, 18501, 18539, 18540, 18541, 18542,
    18543, 18544, 18545, 18546, 18547, 18548, 18549, 18550, 18551, 18552, 18553,
    18554, 18555, 18556, 18557, 18558, 18559, 18560, 18561, 18562, 18563, 18564,
    18565, 18566, 18567, 18568, 18569, 18570, 18571, 18572, 18573, 18574, 18575,
    18576, 18582, 18583, 18584, 18585, 18586, 18587, 18588, 18589, 18590, 18591,
    18592, 18593, 18594, 18595, 18596, 18597, 18598, 18599, 18600, 18601, 18602,
    18603, 18604, 18605, 18606, 18607, 18608, 18609, 18610, 18611, 18612, 18613,
    18614, 18615, 18616, 18617, 18618, 18619, 18620, 18621, 18622, 18623, 18624,
    18625, 18626, 18627, 18628, 18629, 18630, 18631, 18632, 18633, 18634, 18635,
    18636, 18637, 18638, 18639, 18640, 18641, 18642, 18643, 18644, 18645, 18646,
    18647, 18648, 18649, 18650, 18651, 18652, 18653, 18654, 18655, 18656, 18657,
    18658, 18659, 18660, 18661, 18662, 18663, 18664, 18665, 18666, 18667, 18668,
    18669, 18670, 18671, 18672, 18673, 18674, 18675, 18676, 18677
  ]
  _, layers, width, height = get_pdf(which=1, page_number=1)
  celems = layers[0]

  celems = [ celems[idx] for idx in window_schedule_idxes ]
  return layers[0], celems, width, height


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
          elem=child,
          bbox=child.bbox,
          line=None,
          text=child.get_text(),
          child_ids=[]
        )
      )
    elif isinstance(child, pdfminer.layout.LTAnno):
      pass
    elif isinstance(child, pdfminer.layout.LTCurve):
      if child.original_path is not None:
        if child.linewidth > 0:
          lines = path_utils.path_to_lines(path=child.original_path)
          child_nodes: typing.List[ClassificationNode] = []
          for line in lines:
            x0, y0, x1, y1 = line
            xmin = min(x0, x1)
            xmax = max(x0, x1)
            ymin = min(y0, y1)
            ymax = max(y0, y1)
            node = ClassificationNode(
              elem=child,
              bbox=(xmin, ymin, xmax, ymax),
              line=line,
              text=None,
              child_ids=[],
            )
            child_nodes.append(node)
          if create_parents:
            parent_node = ClassificationNode(
              elem=None,
              bbox=child.bbox,
              line=None,
              text=None,
              child_ids=[n.node_id for n in child_nodes]
            )
            for n in child_nodes:
              n.parent_ids.add(parent_node.node_id)
            layers[1].append(parent_node)
          layers[0].extend(child_nodes)

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

def int_bbox(bbox: pdftypes.Bbox):
  return (
    int(bbox[0]),
    int(bbox[1]),
    int(bbox[2]),
    int(bbox[3]),
  )

def what_is_this_test():
  import numpy as np
  _, layers, width, height = get_pdf(which=0, page_number=2)
  celems = layers[0]
  # Instance of "A" <-> Symbol "A"
  #      |                     |
  # Instance of "Alpha" -  Symbol "Alpha"
  step_size = 5
  grid_classified = np.zeros(shape=(height, width), dtype=bool)
  leaf_grid = leafgrid.LeafGrid(celems=celems, step_size=step_size, width=width, height=height)
  bbox = (0, 0, width, height)
  first_text = leaf_grid.first_elem(bbox=bbox, text_only=True)
  print("1:", first_text)
  if first_text is None:
    return
  restrict_idxes: typing.Dict[int, bool] = {}
  x0, y0, x1, y1 = first_text.node.bbox
  nodes_used: typing.List[leafgrid.GridNode] = [first_text]

  x_right = x1
  for next_grid_node in leaf_grid.next_elem_for_coords(
    x0=x0, y0=y0, x1=x1, y1=y1,
    direction=leafgrid.Direction.RIGHT,
    restrict_idxes=restrict_idxes
  ):
    if next_grid_node.node.bbox[0] > x_right + 10:
      break
    print("2:", next_grid_node.node.text)
    nodes_used.append(next_grid_node)
    x_right = next_grid_node.node.bbox[2]
    restrict_idxes[next_grid_node.node_id] = True
    bx0, by0, bx1, by1 = int_bbox(next_grid_node.node.bbox)
    grid_classified[by0:by1, bx0:bx1] = True

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
  node_manager = pdftypes.NodeManager(layers=[layers[0]])
  shape_manager = symbol_indexer.ShapeManager(node_manager=node_manager)
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
  drawer.draw_elems(elems=celems)
  drawer.show("C")
  # Draw elems that activated a symbol enough

def sqft_test():
  # 1 3/4"
  # given an x,y is there a char here?
  # If so grab it, assign its parent to me and continue
  # If it doesn't pan out, destroy parent links
  #_, layers, width, height = get_pdf(which=1, page_number=1)
  _, celems, width, height = get_window_schedule_pdf()

  node_manager = pdftypes.NodeManager(layers=[celems])

  text_join_test_idxes = [118, 119, 120, 121, 122, 123]
  text_join_test = [ celems[idx] for idx in text_join_test_idxes ]
  start_pos_x, start_pos_y = text_join_test[-2].bbox[:2] # 4 in 1 3/4"
  focus_radius = 50
  search_bbox = (
    start_pos_x - focus_radius,
    start_pos_y - focus_radius,
    start_pos_x + focus_radius,
    start_pos_y + focus_radius,
  )

  start_nodes = node_manager.intersection(
    layer_idx=0,
    bbox=search_bbox,
  )

  # Unnatural to only look at one element at a time
  # Look at everything in parallel
  # If I'm looking at x,y and there's a line above, set a boundary there
  # I may need to move my focus
  ytop = start_pos_y + focus_radius
  ybottom = start_pos_y - focus_radius
  xleft = start_pos_x - focus_radius
  xright = start_pos_x + focus_radius
  for node in start_nodes:
    if node.line is not None:
      is_horizontal = abs(node.slope) < 0.1
      is_vertical = abs(node.slope) > path_utils.MAX_SLOPE - 1
      if is_horizontal:
        if node.bbox[1] > start_pos_y:
          ytop = min(ytop, node.bbox[1])
        elif node.bbox[1] < start_pos_y:
          ybottom = max(ybottom, node.bbox[1])
      elif is_vertical:
        if node.bbox[0] > start_pos_x:
          xright = min(xright, node.bbox[0])
        elif node.bbox[0] < start_pos_x:
          xleft = max(xleft, node.bbox[0])
  outer = (xleft, ybottom, xright, ytop)
  inside = [
    n for n in start_nodes if pdfelemtransforms.box_contains(outer=outer, inner=n.bbox)
  ]
  inside.sort(key=lambda n: n.bbox[0])
  text = pdfelemtransforms.join_text_line(nodes=inside)
  parent_node = node_manager.add_node(
    elem=None,
    bbox=outer,
    line=None,
    text=text,
    child_ids=[n.node_id for n in inside],
    layer_id=1,
  )
  for node in inside:
    node.parent_ids.add(parent_node.node_id)
  print(text)
  parent_node.labelize()
  print(parent_node.text, parent_node.labels)
  # Words and known meanings - things start to make sense together
  # Characters connected by position
  # Table elements connected to column header and connected to a row
  # Assign " to mean inches, MAHOG. to mean Mahogany
  return
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=inside, align_top_left=True)
  drawer.show("C")
  return

  manager = symbol_indexer.ShapeManager(leaf_layer=celems)
  manager.activate_layers()


  x_start, y_start = 1022, 1002
  wall_x0, wall_y0, wall_x1, wall_y1 = 886, 889, 1129, 1142
  wall_idxes = [7835, 7837, 8069, 9224]
  # Can't look so narrowly. Luckily with lines we can look more broadly
  # See what lines are connected. Start with path following but protected by the whole context
  # Ex: I don't want to go down that line yet because I saw a horizontal wall nearby that cuts it off
  # 1. See the outside by whitespace
  # 2. Classify the reference lines showing distances by the text
  # 3. Thic

def get_node_neighbors(
  node: ClassificationNode,
  neighbors: typing.List[ClassificationNode]
):
  # TODO: overlap
  closest_above: typing.Union[ClassificationNode, None] = None
  closest_above_space = 1000
  closest_right: typing.Union[ClassificationNode, None] = None
  closest_right_space = 1000
  closest_below: typing.Union[ClassificationNode, None] = None
  closest_below_space = 1000
  closest_left: typing.Union[ClassificationNode, None] = None
  closest_left_space = 1000
  for other in neighbors:
    if other.node_id == node.node_id:
      continue
    is_above = pdfelemtransforms.other_is_pos_cmp(node=node, other=other, vert=True, above=True)
    is_right = pdfelemtransforms.other_is_pos_cmp(node=node, other=other, vert=False, above=True)
    is_below = pdfelemtransforms.other_is_pos_cmp(node=node, other=other, vert=True, above=False)
    is_left = pdfelemtransforms.other_is_pos_cmp(node=node, other=other, vert=False, above=False)
    distance_x = pdfelemtransforms.get_distance_between(this=node.bbox, other=other.bbox, vert=False)
    distance_y = pdfelemtransforms.get_distance_between(this=node.bbox, other=other.bbox, vert=True)
    if is_above and distance_x == 0:
      if closest_above is None or distance_y < closest_above_space:
        closest_above = other
        closest_above_space = distance_y
    if is_right and distance_y == 0:
      if closest_right is None or distance_x < closest_right_space:
        closest_right = other
        closest_right_space = distance_x
    if is_below and distance_x == 0:
      if closest_below is None or distance_y < closest_below_space:
        closest_below = other
        closest_below_space = distance_y
    if is_left and distance_y == 0:
      if closest_left is None or distance_x < closest_left_space:
        closest_left = other
        closest_left_space = distance_x
  return closest_left, closest_below, closest_right, closest_above

def connect_node_neighbors(
  node: ClassificationNode,
  neighbors: typing.List[ClassificationNode],
):
  cl, cb, cr, ca = get_node_neighbors(node=node, neighbors=neighbors)
  node.left = cl
  node.below = cb
  node.right = cr
  node.above = ca

def make_query(node: pdftypes.ClassificationNode):
  x0, y0, x1, y1 = node.bbox
  if node.left_right:
    return (
      x0 - node.width(),
      y0,
      x1 + node.width(),
      y1,
    )
  else:
    return (
      x0,
      y0 - node.height(),
      x1,
      y1 + node.height()
    )

def get_boundaries_str(
  boundaries: pdftypes.Boundaries,
):
  out = "("
  for idx in range(len(boundaries)):
    bound = boundaries[idx]
    if bound is None:
      out += "-1,"
    else:
      out += "{0:.2f},".format(bound[0])
  return out[:-1] + ")"

def set_boundaries(
  start: pdftypes.ClassificationNode,
  node: pdftypes.ClassificationNode,
  boundaries: pdftypes.Boundaries,
):
  if node.line is not None:
    x0, y0, x1, y1 = node.line
    if abs(node.slope) < 0.5 and node.width() >= start.width():
      # Horizontal line
      width_overlap = pdfelemtransforms.get_overlap_in_direction(
        this=start.bbox,
        other=node.bbox,
        height_overlap=False,
      )
      if width_overlap >= start.width():
        if y0 < start.bbox[1]:
          if boundaries[1] is None:
            boundaries[1] = (node.bbox[1], node)
          elif y0 > boundaries[1][0]:
            boundaries[1] = (node.bbox[1], node)
        if y1 > start.bbox[3]:
          if boundaries[3] is None:
            boundaries[3] = (node.bbox[3], node)
          elif y1 < boundaries[3][0]:
            boundaries[3] = (node.bbox[3], node)
    elif abs(node.slope) > 5 and node.height() >= start.height():
      # Vertical line
      height_overlap = pdfelemtransforms.get_overlap_in_direction(
        this=start.bbox,
        other=node.bbox,
        height_overlap=True
      )
      if height_overlap >= start.height():
        if x0 < start.bbox[0]:
          if boundaries[0] is None:
            boundaries[0] = (node.bbox[0], node)
          elif x0 > boundaries[0][0]:
            boundaries[0] = (node.bbox[0], node)
        if x1 > start.bbox[2]:
          if boundaries[2] is None:
            boundaries[2] = (node.bbox[2], node)
          elif x1 < boundaries[2][0]:
            boundaries[2] = (node.bbox[2], node)

FONT_SIZE_DIFF = 1

def node_should_add_to_group(
  start: pdftypes.ClassificationNode,
  node: pdftypes.ClassificationNode,
  group: typing.Set[pdftypes.ClassificationNode],
):
  if node in group:
    return False
  node.labelize()
  radius = 1
  if start.text is not None and node.text is not None:
    if node.left_right != start.left_right:
      return False
    if abs(node.fontsize - start.fontsize) > FONT_SIZE_DIFF:
      return False
    idx0, idx1 = pdfelemtransforms.get_idx_for_vert(vert=not start.left_right)
    perpendicular_overlap = pdfelemtransforms.get_overlap_in_direction(
      this=start.bbox,
      other=node.bbox,
      height_overlap=start.left_right,
    )
    start_perpendicular_size = start.height() if start.left_right else start.width()
    if abs(perpendicular_overlap - start_perpendicular_size) > FONT_SIZE_DIFF:
      if start.labels[pdftypes.LabelType.FRACTION] > 0:
        if perpendicular_overlap / start_perpendicular_size > 0.25:
          # Enough overlap
          if start.bbox[idx0] < node.bbox[idx0] and start.bbox[idx1] > node.bbox[idx1]:
            # Centered
            return True
      return False

    node_is_touching_left = abs(node.bbox[idx1] - start.bbox[idx0]) < radius
    node_is_touching_right = abs(node.bbox[idx0] - start.bbox[idx1]) < radius
    if node_is_touching_left or node_is_touching_right:
      return True
  return False

def cluster_text_group(
  start: pdftypes.ClassificationNode,
  leaf_grid: leafgrid.LeafGrid,
):
  # Get my neighbors, find what I'm connected to
  # If I'm text then I don't connect to a much larger line
  # Joined text can connect to a large line if they are above the same size
  # Keep connecting until no nodes in my group can connect
  query = make_query(node=start)
  neighbors = leaf_grid.intersection(query=query)

  group: typing.Set[pdftypes.ClassificationNode] = set()
  group.add(start)
  to_process: typing.List[pdftypes.ClassificationNode] = [start]

  while len(to_process) > 0:
    added_node = to_process.pop()
    query = make_query(node=added_node)
    neighbors = leaf_grid.intersection(query=query)
    neighbors.sort(key=lambda n: pdfelemtransforms.get_node_distance_to(other=n, src=added_node))
    for node in neighbors:
      if node_should_add_to_group(start=added_node, node=node, group=group):
        group.add(node)
        to_process.append(node)
      # TODO: instead of boundaries, stop going in that direction
      # TODO: if reaching a fraction, form the fraction group then continue
      # elif I'm a number
      # depending on where I am relative to added_node
      # check above,left,right,below to see if I'm a fraction
      # elif group is a fraction (numerator/denominator)
      # check above,left,right,below to see if I'm a fraction
      # if fraction, to_process.append(fraction_node) with new height
  out = list(group)
  return out

def cluster_text_by_connected_groups(
  node_manager: pdftypes.NodeManager,
  leaf_grid: leafgrid.LeafGrid,
):
  nodes_used: typing.Set[
    pdftypes.ClassificationNode,
  ] = set()
  text_nodes = set([n for n in node_manager.nodes.values() if n.text is not None])
  remaining = text_nodes.difference(nodes_used)
  groups: typing.List[
    typing.List[pdftypes.ClassificationNode],
  ] = []
  # remaining = [ node_manager.nodes[17275]] # H in HARDWARE
  # remaining = [node_manager.nodes[3282]]
  # remaining = [ node_manager.nodes[17229]] # schedule 3 in 3/4
  # remaining = [ node_manager.nodes[17227]] # schedule 1 in 1 3/4
  # remaining = [ node_manager.nodes[19926], node_manager.nodes[19949]]
  # TODO: Fix: remaining = [ node_manager.nodes[19926], node_manager.nodes[19949]]
  # TODO: Fix: remaining = [ node_manager.nodes[21200]]
  # TODO: Join [2348, 2390, 3447, 3448, 3454, 3455, 3456, 3457, 3458, 3466, 3467, 3468, 3469, 3470, 3471]
  #    - Use known words
  is_dev = len(remaining) <= 2
  while len(remaining) > 0:
    start_node = remaining.pop()

    if is_dev:
      print("Start:", start_node.bbox, start_node.text)
    group = cluster_text_group(
      start=start_node, leaf_grid=leaf_grid
    )
    for node in group:
      nodes_used.add(node)
    groups.append(group)
    if not is_dev:
      remaining = text_nodes.difference(nodes_used)
  return groups


def conn_test():
  #_, celems, width, height = get_window_schedule_pdf()
  _, layers, width, height = get_pdf(which=1, page_number=1)
  celems = layers[0]


  node_manager = pdftypes.NodeManager(layers=[celems])
  leaf_grid = leafgrid.LeafGrid(celems=celems, width=width, height=height, step_size=5)

  text_join_test_idxes = [118, 119, 120, 121, 122, 123]
  text_join_test = [ celems[idx] for idx in text_join_test_idxes ]
  start_node = text_join_test[-2]

  groups = cluster_text_by_connected_groups(
    node_manager=node_manager,
    leaf_grid=leaf_grid
  )
  print("Got groups", len(groups))
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=celems, align_top_left=False)

  for group in groups:
    bbox = pdfelemtransforms.bounding_bbox(elems=group)
    # drawer.draw_elems(elems=group, align_top_left=False)
    drawer.draw_bbox(bbox=bbox, color="blue")
    group.sort(key=lambda n: n.bbox[0])
    #text = pdfelemtransforms.join_text_line(nodes=group)

  drawer.show("")
  return
  for n in group:
    print(n.text, n.left_right, n.slope)
  # TODO: Pick a boundary that actually applies
  # TODO: Text may be close enough but should be separate groups
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=[*group, *[b for b in boundaries if b is not None]], align_top_left=False)
  drawer.show("")
  return

  start_pos_x, start_pos_y = start_node.bbox[:2] # 4 in 1 3/4"
  focus_radius = 50
  search_bbox = (
    start_pos_x - focus_radius,
    start_pos_y - focus_radius,
    start_pos_x + focus_radius,
    start_pos_y + focus_radius,
  )
  start_node.labelize()

  leaf_neighbors = node_manager.intersection(
    layer_idx=0,
    bbox=search_bbox,
  )
  connect_node_neighbors(node=start_node, neighbors=leaf_neighbors)
  # Fraction rule that activates --shapememory activates a fraction
  drawer.draw_elems(elems=leaf_neighbors, align_top_left=True)
  for n in leaf_neighbors:
    drawer.draw_bbox(bbox=n.bbox, color="blue")
  drawer.show("C", blocking=True)

  cl, cb, cr, ca = start_node.left, start_node.below, start_node.right, start_node.above
  for n in [cl, cb, cr, ca]:
    if n is not None:
      n.labelize()
  if start_node.labels[LabelType.INT] > 0:
    if cr is not None:
      if cr.labels[LabelType.MEASUREMENT] > 0:
        # check what is to the right of cr
        pass
    if cl is not None and cl == ca and cl.labels[LabelType.FRACTION_LINE] > 0:
      cmp_height = cl.height() - start_node.height()
      if 0 <= cmp_height and cmp_height < start_node.height() * 3:
        print("Join /{0}".format(start_node.text))
      # divisor keep looking left

  draw = [start_node, *[n for n in [cl, cb, cr, ca] if n is not None]]
  left_itr = cl
  while left_itr is not None:
    connect_node_neighbors(node=left_itr, neighbors=leaf_neighbors)
    left_itr = left_itr.left
    if left_itr is not None:
      draw.append(left_itr)


  for d in leaf_neighbors:
    d.labelize()
    #print(d.text, d.labels)
  print("Start:", start_node)
  print("left:", cl)
  print("below:", cb)
  print("right:", cr)
  print("above:", ca)


  # TODO: Not a grid, instead pointers
  # We can efficiently do this by dividing regions into groups
  # non-rectangular but simply lists of elements where each group is surrounded by space
  # Clustering algorithm?
  # Humans pick a focus area and expand until a region is captured and ignore everything outside
  # Don't optimize yet, just get something working first
  # Given x, pointer to left, up, right, down given my width, height
  # '3', '/', '8' grouped then '1', ' ', '3/8', '"'  grouped into '1 3/8"'
  # because 3/8 takes precedence over 8"
  # [                                    line                               ]
  #      [line][      space       ][line][     space    ][line]
  #      [line][space]1 3/4"[space][line][space]H4[space][line]
  #      [line][      space       ][line][     space    ][line]

@dataclasses.dataclass(order=True)
class AStarNode():
  sort_score: float = dataclasses.field(compare=True)
  def __init__(
    self,
    score: float,
    label: pdftypes.LabelType,
    node: pdftypes.ClassificationNode) -> None:
    self.score = score
    self.sort_score = -score
    self.label = label
    self.node = node

def a_star_join(
  start: pdftypes.ClassificationNode,
  nodes: typing.List[pdftypes.ClassificationNode]
):
  q: typing.List[AStarNode] = []
  start.labelize()
  print("a_star_join", start.text)
  for node in nodes:
    node.labelize()
  for label, score in start.labels.items():
    if score > 0:
      heapq.heappush(q, AStarNode(score=score, label=label, node=start))
  stranded: typing.List[AStarNode] = []

  while len(q) > 0:
    item = heapq.heappop(q)
    label = item.label
    nodes.sort(key=lambda n: pdfelemtransforms.get_node_distance_to(other=n, src=item.node))
    if label == LabelType.NUMBER or label == LabelType.MEASUREMENT:
      for node in nodes:
        if node.node_id == item.node.node_id:
          continue
        dist = pdfelemtransforms.get_node_distance_to(other=node, src=item.node)
        angles = pdfelemtransforms.get_node_angles_to(other=node, src=item.node)
        angles_str = " ".join(["{0:.2f}".format(angle) for angle in angles])
        print("Dist:{0:.2f} Angles:{1}".format(dist, angles_str),
          "Text:", node.text,
          "slope:{0:.2f} length:{1:.2f}".format(node.slope, node.length))

def get_horizontal_aligned_groups(
  nodes: typing.List[pdftypes.ClassificationNode]
):
  # We'll get a little confused with the 3/4
  # but that will be fixed when merging the 3/4 into a single element
  tb_groups: typing.DefaultDict[
    typing.Tuple[float, float],
    typing.Set[pdftypes.ClassificationNode]
  ] = collections.defaultdict(set)
  for node in nodes:
    _, y0, _, y1 = node.bbox
    yb = math.floor(y0)
    yt = math.floor(y1)
    tb_groups[yb, yt].add(node)
  merged_groups: typing.DefaultDict[
    typing.Tuple[float, float],
    typing.Set[pdftypes.ClassificationNode]
  ] = collections.defaultdict(set)
  for (yb, yt), line_nodes in tb_groups.items():
    dest = (yb, yt)
    merge_range =  [(yb, yt), (yb+1, yt), (yb, yt+1), (yb+1, yt+1)]
    for merge_key in merge_range:
      if merge_key in merged_groups:
        dest = merge_key
        break
    merged_groups[dest] |= line_nodes
    for merge_key in merge_range[1:]:
      if merge_key in tb_groups:
        merge_group = tb_groups[merge_key]
        merged_groups[dest] |= merge_group

  return merged_groups

def align_horizontal(
  nodes: typing.List[pdftypes.ClassificationNode]
):
  horizontal_groups = get_horizontal_aligned_groups(nodes=nodes)
  # TODO: Merge groups that share a lot of area that are close
  # Ex: (553, 562), (557, 563), (554, 562), (552, 559) => (552, 563)
  # But (1312, 553, 1319, 562) doesn't merge because it's x is far away
  # Later we see that the table row is everything inside (1029, 549, 1651, 567)
  return horizontal_groups

def align_vertical():
  pass

def fraction_test():
  _, layers, width, height = get_pdf(which=1, page_number=1)
  node_manager = pdftypes.NodeManager(layers=[layers[0]])
  measurement_fraction_vert_idxes = [6681, 6682, 6683, 6684, 6685, 6686, 6687, 6688, 6689, 6690, 6691]
  measurement_fraction_horiz_idxes = [6618, 6619, 6620, 6621, 6622, 6623, 6624, 6625, 6626, 6627]
  fraction_schedule_idxes = [17107, 17108, 17125, 17126, 17227, 17228, 17229, 17230, 17231, 17232]
  start_node = layers[0][fraction_schedule_idxes[-1]] # -1, -2
  x0, y0, x1, y1 = start_node.bbox

  leaf_grid = leafgrid.LeafGrid(celems=layers[0], width=width, height=height, step_size=5)

  if start_node.left_right:
    radius = start_node.width()
    query = (
      x0-radius,
      y0,
      x1+radius,
      y1,
    )
  else:
    radius = start_node.height()
    query = (
      x0,
      y0-radius,
      x1,
      y1+radius,
    )

  grid_elems = leaf_grid.intersection(query=query)
  grid_elems.sort(key=lambda n: pdfelemtransforms.get_node_distance_to(other=n, src=start_node))
  # if horizontally aligned and touching continue
  #

  horiz_groups = align_horizontal(nodes=grid_elems)
  for (yb, yt), line_nodes in horiz_groups.items():
    print("y0:{0:.2f} y1:{1:.2f} num:{2}".format(yb, yt, len(line_nodes)))

  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=grid_elems, align_top_left=True)
  for elem in grid_elems:
    drawer.draw_bbox(bbox=elem.bbox, color="blue")
  drawer.draw_bbox(bbox=query, color="red")
  drawer.show("")

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
  parser.add_argument("--conn", dest="conn", default=False, action="store_true")
  parser.add_argument("--fraction", dest="fraction", default=False, action="store_true")
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
  elif args.conn:
    func = conn_test
  elif args.fraction:
    func = fraction_test
  if func:
    if args.profile:
      cProfile.run("{0}()".format(func.__name__))
    else:
      func()

if __name__ == "__main__":
  main()
