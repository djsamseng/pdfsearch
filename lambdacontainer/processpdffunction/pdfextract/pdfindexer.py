
import collections
import time
import typing

import numpy as np
import rtree
import scipy.spatial # type: ignore

from . import path_utils
from .ltjson import LTJson

LOG_TIME = False

class PdfIndexer:
  # To find contents inside shapes
  find_by_position_rtree: rtree.index.Index
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
      print("pdfindexer rtree:", t1-t0, "kdtree:", t3-t2, "total:", t3-tb)

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

  def find_top_left_in(
    self,
    bbox: typing.Tuple[float, float, float, float],
  ) -> typing.List[LTJson]:
    result_idxes = self.find_by_position_rtree.intersection(coordinates=bbox)
    if result_idxes is None:
      return []
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

  def find_similar_shapes(
    self,
    wrapper_to_find: LTJson,
    query_radius: float,
  ) -> typing.List[LTJson]:
    t0 = time.time()
    similar_height_width = self.find_similar_height_width(
      width=wrapper_to_find.width,
      height=wrapper_to_find.height,
      query_radius=query_radius
    )
    t1 = time.time()
    if wrapper_to_find.original_path is not None:
      t2 = time.time()
      ret = find_similar_curves(wrapper_to_find=wrapper_to_find, wrappers_to_search=similar_height_width, max_dist=query_radius)
      t3 = time.time()
      if LOG_TIME:
        print("find_similar_shapes kdtree:", t1-t0, "loop reduce:", t3-t2)
      return ret
    return []

def line_distance(
  linea: path_utils.LinePointsType,
  lineb: path_utils.LinePointsType,
):
  (x0a, y0a), (x1a, y1a) = linea
  (x0b, y0b), (x1b, y1b) = lineb
  dist_forward = np.abs(x0a-x0b) + np.abs(y0a-y0b) + np.abs(x1a-x1b) + np.abs(y1a-y1b)
  dist_backward = np.abs(x0a-x1b) + np.abs(y0a-y1b) + np.abs(x1a-x0b) + np.abs(y1a-y0b)
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
def find_similar_curves(
  wrapper_to_find: LTJson,
  wrappers_to_search: typing.List[LTJson],
  max_dist: float,
) -> typing.List[LTJson]:
  lines_to_find = wrapper_to_find.get_zeroed_path_lines()
  if wrapper_to_find.width <= 0.1:
    return []
  to_find_h_w_ratio = wrapper_to_find.height / wrapper_to_find.width
  if len(lines_to_find) == 0:
    return []

  results: typing.List[LTJson] = []
  for wrapper in wrappers_to_search:
    if wrapper.width <= 0.1:
      continue
    potential_h_w_ratio = wrapper.height / wrapper.width
    if abs(to_find_h_w_ratio - potential_h_w_ratio) > 0.1:
      continue
    potential_lines = wrapper.get_zeroed_path_lines()
    if len(potential_lines) == 0:
      continue
    # TODO: line distance by area drawn instead of just start/stop
    # TODO: size agnostic
    dist = line_set_distance(lines1=lines_to_find, lines2=potential_lines, max_dist=max_dist)
    if dist < max_dist:
      results.append(wrapper)

  return results
