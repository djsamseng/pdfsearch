

import collections
import cProfile
import dataclasses
import heapq
import os
import math
import random
import pickle
import typing
import argparse
import json

import pdfminer.high_level, pdfminer.utils, pdfminer.layout
import rtree

from pdfextract import path_utils, pdftypes
from pdfextract import pdfelemtransforms
from pdfextract import pdfindexer, symbol_indexer, leafgrid, textjoiner
from pdfextract import pdftkdrawer, classifier_drawer
from pdfextract.ltjson import LTJson
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
      ClassificationNode.id_itr = len(celems[0])
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

def get_rounded_bbox(bbox: Bbox):
  return (
    math.floor(bbox[0]),
    math.floor(bbox[1]),
    math.ceil(bbox[2]),
    math.ceil(bbox[3]),
  )

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
    direction=pdftypes.Direction.RIGHT,
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
  # TODO: Look at the schedule, find all the 101,102 etc. notice they all have a circle around them
  window_label_with_pointer_line_ids = [6602, 6603, 6604, 6605, 6606, 6607, 6608]
  door_label_line_ids = [7925, 7926, 7927, 7928, 7929, 7930, 7931, 7932, 7933, 7934,
    7935, 7936, 7937, 7938, 7939, 7940, 7941, 7942, 7943, 7944, 7945, 7946, 7947, 7948,
    7949, 7950, 7951, 7952, 7953, 7954, 7955, 7956, 7957, 7958, 7959, 7960, 7961, 7962, 7963, 7964]

  node_manager = pdftypes.NodeManager(layers=[layers[0]])
  window_label_with_pointer_line = [
    node_manager.nodes[node_id] for node_id in window_label_with_pointer_line_ids
  ]
  door_labels = [
    node_manager.nodes[node_id] for node_id in door_label_line_ids
  ]
  window_labels = window_label_with_pointer_line[:-1]
  shape_manager = symbol_indexer.ShapeManager(node_manager=node_manager)
  shape_manager.add_shape(
    shape_id="window_label",
    lines=[l.line for l in window_labels if l.line is not None]
  )
  shape_manager.add_shape(
    shape_id="door_label",
    lines=[l.line for l in door_labels if l.line is not None]
  )
  run_shapememory(
    node_manager=node_manager,
    shape_manager=shape_manager,
    width=width,
    height=height,
  )

def lighting_test():
  _, layers, width, height = get_pdf(which=1, page_number=2)
  node_manager = pdftypes.NodeManager(layers=[layers[0]])
  shape_manager = symbol_indexer.ShapeManager(node_manager=node_manager)
  lighting_a_ids = [25891, 25892, 25893, 25894, 25895, 25896, 25897, 25898, 25899, 25900, 25901,
    25902, 25903, 25904, 25905, 25906, 25907, 25908, 25909, 25910, 25911, 25912, 25913, 25914,
    25915, 25916, 25917, 25918, 25919, 25920, 25921, 25922, 25923, 25924, 25925, 25926, 25927,
    25928, 25929, 25930, 25931, 25932, 25933, 25934, 25935, 25936, 25937, 25938, 25939, 25940,
    25941, 25942, 25943, 25944, 25945, 25946, 25947, 25948, 25949, 25950, 25951, 25952, 25953,
    25954, 25955, 25956, 25957, 25958, 25959, 25960, 25961, 25962, 25963, 25964, 25965, 25966,
    25967, 25968, 25969, 25970, 25971, 25972]
  lighting_a = [node_manager.nodes[node_id] for node_id in lighting_a_ids]
  lighting_c_ids = [25334, 25335, 25336, 25337, 25338, 25339, 25340, 25341, 25342, 25343, 25344,
    25345, 25346, 25347, 25348, 25349, 25350, 25351, 25352, 25353, 25354, 25355, 25356, 25357,
    25358, 25359, 25360, 25361, 25362, 25363, 25364, 25365, 25366, 25367, 25368, 25369, 25370,
    25371, 25372, 25373, 25374, 25375, 25376, 25377, 25378, 25379, 25380, 25381, 25382, 25383,
    25384, 25385, 25386, 25387, 25388, 25389, 25390, 25391, 25392, 25393, 25394, 25395, 25396,
    25397, 25398, 25399, 25400, 25401, 25402, 25403, 25404, 25405, 25406, 25407, 25408, 25409,
    25410, 25411, 25412, 25413]
  lighting_c = [node_manager.nodes[node_id] for node_id in lighting_c_ids]
  lighting_e_ids = [25593, 25594, 25595, 25596, 25597, 25598]
  lighting_e = [node_manager.nodes[node_id] for node_id in lighting_e_ids]
  shape_manager.add_shape(
    shape_id="lighting_a",
    lines=[l.line for l in lighting_a if l.line is not None]
  )
  shape_manager.add_shape(
    shape_id="lighting_c",
    lines=[l.line for l in lighting_c if l.line is not None]
  )
  shape_manager.add_shape(
    shape_id="lighting_e",
    lines=[l.line for l in lighting_e if l.line is not None]
  )

  run_shapememory(
    node_manager=node_manager,
    shape_manager=shape_manager,
    width=width,
    height=height,
  )

def color_for_idx(idx: int):
  if idx == 0:
    return "blue"
  elif idx == 1:
    return "red"
  elif idx == 2:
    return "green"
  else:
    return "purple"

def run_shapememory(
  node_manager: pdftypes.NodeManager,
  shape_manager: symbol_indexer.ShapeManager,
  width: int,
  height: int,
):
  print("Layers before:", [len(l) for l in node_manager.layers.values()])
  nodes_used = shape_manager.activate_layers()
  print("Layers after:", [len(l) for l in node_manager.layers.values()])
  #nodes_used_b = shape_manager.activate_layers()
  #assert len(nodes_used_b) == 0, "Second activation got nodes: {0}".format(nodes_used_b)
  # print("Layers after:", [len(l) for l in layers])
  # TODO: use children_idxes of shape_manager.results to draw recursively

  results = shape_manager.results
  draw_layer = 0
  draw_nodes = [node_manager.nodes[node_id] for node_id in node_manager.layers[draw_layer]]
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=draw_nodes, align_top_left=False)
  for idx, (shape_id, shape_elems) in enumerate(results.items()):
    color = color_for_idx(idx=idx)
    for found in shape_elems:
      drawer.draw_bbox(bbox=found.bbox, color=color)
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
    left_right=inside[0].left_right,
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

  manager = symbol_indexer.ShapeManager(node_manager=node_manager)
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



def conn_test():
  #_, celems, width, height = get_window_schedule_pdf()
  _, layers, width, height = get_pdf(which=1, page_number=1)
  celems = layers[0]


  node_manager = pdftypes.NodeManager(layers=[celems])
  #leaf_grid = leafgrid.LeafGrid(celems=celems, width=width, height=height, step_size=5)

  text_join_test_idxes = [118, 119, 120, 121, 122, 123]
  text_join_test = [ celems[idx] for idx in text_join_test_idxes ]
  start_node = text_join_test[-2]

  groups, fractions, fraction_text_groups = textjoiner.cluster_text(node_manager=node_manager)

  draw_layer = 0
  draw_nodes = [node_manager.nodes[node_id] for node_id in node_manager.layers[draw_layer]]
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=draw_nodes, align_top_left=False)

  for group in groups:
    bbox = group.bbox# pdfelemtransforms.bounding_bbox(elems=group)
    # drawer.draw_elems(elems=group, align_top_left=False)
    drawer.draw_bbox(bbox=bbox, color="blue")
  for fraction_parent in fractions:
    drawer.draw_bbox(bbox=fraction_parent.bbox, color="red")
    #text = pdfelemtransforms.join_text_line(nodes=group)
  for fraction_text_group in fraction_text_groups:
    drawer.draw_bbox(bbox=fraction_text_group.bbox, color="green")
  drawer.show("")
  return
  for n in group:
    print(n.text, n.left_right, n.slope)
  # TODO: Pick a boundary that actually applies
  # TODO: Text may be close enough but should be separate groups
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=group, align_top_left=False)
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
  textjoiner.connect_node_neighbors(node=start_node, neighbors=leaf_neighbors)
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
    textjoiner.connect_node_neighbors(node=left_itr, neighbors=leaf_neighbors)
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
  stranded: typing.List[AStarNode] = [] # type: ignore

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
  node_manager = pdftypes.NodeManager(layers=[layers[0]]) # type: ignore
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

def see_test():
  _, layers, width, height = get_pdf(which=1, page_number=1) # type: ignore
  node_manager = pdftypes.NodeManager(layers=[layers[0]])  # type: ignore
  # Grab a spot, see what actions are triggered by the activations
  # Desire = "find sqft of bedroom"
  #   - Need = bedroom boundaries
  #   - Need = distance measurements
  #   - Need = distance measurements -> sqft calculator
  # Action = scan until bedroom activates
  # Action = scan for bedroom walls
  # Action = scan for wall distance labels

  # Convolve
  # First a quick scan at small dx/dy to build up an initial hypothesis
  # Merge areas
  # Then go back down and refine
  # Edit text joiner to look at more than just the processing node
  # and take action depending on the situation on where to look

  draw_layer = 0
  draw_nodes = [node_manager.nodes[node_id] for node_id in node_manager.layers[draw_layer]]
  drawer = classifier_drawer.ClassifierDrawer(width=width, height=height, select_intersection=True)
  drawer.draw_elems(elems=draw_nodes, align_top_left=False)
  drawer.show("")

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--profile", dest="profile", default=False, action="store_true")
  parser.add_argument("--what", dest="what", default=False, action="store_true") # TODO: continue to form words
  parser.add_argument("--shapememory", dest="shapememory", default=False, action="store_true")
  parser.add_argument("--lighting", dest="lighting", default=False, action="store_true")
  parser.add_argument("--sqft", dest="sqft", default=False, action="store_true")
  parser.add_argument("--conn", dest="conn", default=False, action="store_true")
  parser.add_argument("--fraction", dest="fraction", default=False, action="store_true")
  parser.add_argument("--see", dest="see", default=False, action="store_true")
  return parser.parse_args()

def main():
  args = parse_args()
  func = None
  if args.what:
    func = what_is_this_test
  elif args.shapememory:
    func = shapememory_test
  elif args.lighting:
    func = lighting_test
  elif args.sqft:
    func = sqft_test
  elif args.conn:
    func = conn_test
  elif args.fraction:
    func = fraction_test
  elif args.see:
    func = see_test
  if func:
    if args.profile:
      cProfile.run("{0}()".format(func.__name__))
    else:
      func()

if __name__ == "__main__":
  main()
