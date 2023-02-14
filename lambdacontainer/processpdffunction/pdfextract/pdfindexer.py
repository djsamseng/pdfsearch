
import collections
import time
import typing

import rtree
import scipy.spatial # type: ignore

from . import path_utils
from .ltjson import LTJson, BboxType

LOG_TIME = False

class PdfLineIndexer:
  def __init__(
    self,
    elems: typing.List[LTJson]
  ) -> None:
    self.elems = elems
    # Manually saving rtree_id_to_elem_idx
    # 14464    0.026    0.000    0.820    0.000 pdfindexer.py:44(find_intersection)
    # Saving elem_idx in the rtree and using objects="raw"
    # 14464    0.034    0.000    5.196    0.000 pdfindexer.py:44(find_intersection)
    self.rtree_id_to_elem_idx: typing.List[int] = []
    def insertion_generator(elems: typing.List[LTJson], rtree_id_to_elem_idx: typing.List[int]):
      rtree_id = 0
      for elem_idx, elem in enumerate(elems):
        lines = elem.get_path_lines()
        if elem.text is not None and len(lines) == 0:
          yield (rtree_id, elem.bbox, None)
          rtree_id_to_elem_idx.append(elem_idx)
          rtree_id += 1
        else:
          for line in lines:
            x0, y0, x1, y1, = line
            yield (rtree_id, (x0, y0, x1, y1), None)
            rtree_id_to_elem_idx.append(elem_idx)
            rtree_id += 1
    self.find_by_position_rtree = rtree.index.Index(
      insertion_generator(elems=elems, rtree_id_to_elem_idx=self.rtree_id_to_elem_idx),
    )

  def find_intersection(
    self,
    bbox: BboxType,
  ) -> typing.List[LTJson]:
    result_idxes = self.find_by_position_rtree.intersection(bbox, objects=False)
    result_idxes = typing.cast(typing.List[int], result_idxes)
    results = [ self.elems[self.rtree_id_to_elem_idx[rtree_id]] for rtree_id in result_idxes ] #pylint: disable=not-an-iterable
    return results

class PdfIndexer:
  # To find contents inside shapes
  find_by_position_rtree: rtree.index.Index
  line_indexer: PdfLineIndexer
  # To find similar shapes
  find_by_shape_kdtree: scipy.spatial.KDTree
  def __init__(
    self,
    wrappers: typing.List[LTJson],
    page_width: float,
    page_height: float,
  ) -> None:
    tb = time.time()
    self.page_width = page_width
    self.page_height = page_height
    self.wrappers = wrappers
    tl0 = time.time()
    self.line_indexer = PdfLineIndexer(elems=wrappers)
    tl1 = time.time()
    def index_insertion_generator(elems: typing.List[LTJson]):
      for i, wrapper in enumerate(elems):
        yield (i, wrapper.bbox, i)

    t0 = time.time()
    self.find_by_position_rtree = rtree.index.Index(index_insertion_generator(elems=wrappers))
    t1 = time.time()
    all_elem_shapes = [[wrapper.width, wrapper.height] for wrapper in wrappers]
    t2 = time.time()
    self.find_by_shape_kdtree = scipy.spatial.KDTree(data=all_elem_shapes)
    t3 = time.time()
    self.text_lookup: typing.Dict[str, typing.List[LTJson]] = collections.defaultdict(list)
    for elem in wrappers:
      if elem.text is not None:
        key_text = elem.text.replace("\n", " ").lower().strip()
        self.text_lookup[key_text].append(elem)
    if LOG_TIME:
      # 0.25s 0.9s 0.009s total:1.2s
      print("pdfindexer rtree:", t1-t0, "lineindexer:", tl1-tl0, "kdtree:", t3-t2, "total:", t3-tb)

  def find_contains(
    self,
    bbox: typing.Tuple[float, float, float, float],
    y_is_down: bool = False,
  ) -> typing.List[LTJson]:
    '''
    bbox = x0, y0, x1, y1
    '''
    if y_is_down:
      x0, y0, x1, y1 = bbox
      bbox = (x0, self.page_height - y1, x1, self.page_height - y0)
    result_idxes = self.find_by_position_rtree.contains(bbox)
    if result_idxes is None:
      return []
    result_idxes = list(result_idxes)
    results = [self.wrappers[idx] for idx in result_idxes]
    return results

  def find_intersection(
    self,
    bbox: BboxType,
    y_is_down: bool = False,
  ) -> typing.List[LTJson]:
    if y_is_down:
      x0, y0, x1, y1 = bbox
      bbox = (x0, self.page_height - y1, x1, self.page_height - y0)
    return self.line_indexer.find_intersection(bbox)

  def find_top_left_in(
    self,
    bbox: typing.Tuple[float, float, float, float],
  ) -> typing.List[LTJson]:
    result_idxes = self.find_by_position_rtree.intersection(coordinates=bbox)
    result_idxes = list(result_idxes)
    results = [ self.wrappers[idx] for idx in result_idxes ]
    def starts_inside_bbox(elem: LTJson, bbox: typing.Tuple[float, float, float, float]):
      x0, y0, x1, y1 = bbox
      left_x, _, _, top_y = elem.bbox
      return left_x >= x0 and left_x <= x1 and top_y >= y0 and top_y <= y1
    results = [ r for r in results if starts_inside_bbox(elem=r, bbox=bbox)]
    return results

  def find_similar_height_width(
    self,
    width: float,
    height: float,
    query_radius: float,
  ) -> typing.List[LTJson]:
    search_shape = [width, height]
    result_idxes: typing.List[int] = self.find_by_shape_kdtree.query_ball_point(x=search_shape, r=query_radius) # type: ignore
    results = [self.wrappers[idx] for idx in result_idxes]
    return results

def line_distance(
  linea: path_utils.LinePointsType,
  lineb: path_utils.LinePointsType,
):
  x0a, y0a, x1a, y1a = linea
  x0b, y0b, x1b, y1b = lineb
  dist_forward = abs(x0a-x0b) + abs(y0a-y0b) + abs(x1a-x1b) + abs(y1a-y1b)
  dist_backward = abs(x0a-x1b) + abs(y0a-y1b) + abs(x1a-x0b) + abs(y1a-y0b)
  return min(dist_forward, dist_backward)

def line_set_distance(
  lines1: typing.List[path_utils.LinePointsType],
  lines2: typing.List[path_utils.LinePointsType],
  max_dist: float,
):
  total_dist = 0.
  if len(lines1) == 0 or len(lines2) == 0:
    return total_dist

  for linea in lines1:
    best_dist = line_distance(linea=linea, lineb=lines2[0])
    for lineb in lines2:
      dist = line_distance(linea=linea, lineb=lineb)
      best_dist = min(best_dist, dist)
    total_dist += best_dist / max(len(lines1), len(lines2))
    if max_dist >= 0 and total_dist > max_dist:
      # Return early
      return total_dist
  return total_dist

# TODO: Search for union of multiple wrappers_to_find

def find_most_similar_curve(
  wrapper_to_find: LTJson,
  wrappers_to_search: typing.List[LTJson],
  max_dist: float,
) -> typing.List[LTJson]:
  lines_to_find = wrapper_to_find.get_zeroed_path_lines()
  if len(lines_to_find) == 0:
    return []

  if wrapper_to_find.width <= 0.1:
    to_find_h_w_ratio = 1000
  else:
    to_find_h_w_ratio = min(1000, wrapper_to_find.height / wrapper_to_find.width)

  results: typing.List[LTJson] = []
  best_dist = None
  for wrapper in wrappers_to_search:
    if wrapper.width <= 0.1:
      potential_h_w_ratio = 1000
    else:
      potential_h_w_ratio = min(1000, wrapper.height / wrapper.width)
    if abs(to_find_h_w_ratio - potential_h_w_ratio) > 0.1:
      continue
    potential_lines = wrapper.get_zeroed_path_lines()
    if len(potential_lines) == 0:
      continue
    # TODO: line distance by area drawn instead of just start/stop
    # TODO: size agnostic
    dist = line_set_distance(lines1=lines_to_find, lines2=potential_lines, max_dist=max_dist)
    if dist < max_dist:
      if best_dist is None or dist < best_dist:
        best_dist = dist
        results = [wrapper]

  return results
