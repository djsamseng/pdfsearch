import typing

import numpy as np
import rtree
import scipy.spatial # type: ignore

import path_utils
import pdfextracter

class PdfIndexer:
  # To find contents inside shapes
  find_by_position_rtree: rtree.index.Index
  # To find similar shapes
  find_by_shape_kdtree: scipy.spatial.KDTree
  def __init__(
    self,
    wrappers: typing.List[pdfextracter.LTJson],
    page_width: int,
    page_height: int,
  ) -> None:
    self.page_width = page_width
    self.page_height = page_height
    self.wrappers = wrappers
    def index_insertion_generator(elems: typing.List[pdfextracter.LTJson]):
      for i, wrapper in enumerate(elems):
        yield (i, wrapper.bbox, i)

    self.find_by_position_rtree = rtree.index.Index(index_insertion_generator(elems=wrappers))
    all_elem_shapes = [[wrapper.width, wrapper.height] for wrapper in wrappers]
    self.find_by_shape_kdtree = scipy.spatial.KDTree(data=all_elem_shapes)

  def find_contains(
    self,
    bbox: typing.Tuple[float, float, float, float],
    y_is_down: bool = False,
  ) -> typing.List[pdfextracter.LTJson]:
    '''
    bbox = x0, y0, x1, y1
    '''
    if y_is_down:
      x0, y0, x1, y1 = bbox
      bbox = (x0, self.page_height - y1, x1, self.page_height - y0)
    result_idxes = self.find_by_position_rtree.contains(bbox)
    if result_idxes is None:
      return []
    results = [self.wrappers[idx] for idx in result_idxes]
    return results

  def find_similar_height_width(
    self,
    width: float,
    height: float,
    query_radius: float,
  ) -> typing.List[pdfextracter.LTJson]:
    search_shape = [width, height]
    result_idxes: typing.List[int] = self.find_by_shape_kdtree.query_ball_point(x=search_shape, r=query_radius) # type: ignore
    results = [self.wrappers[idx] for idx in result_idxes]
    return results

  def find_similar_shapes(
    self,
    wrapper_to_find: pdfextracter.LTJson,
    query_radius: float,
  ) -> typing.List[pdfextracter.LTJson]:
    similar_height_width = self.find_similar_height_width(
      width=wrapper_to_find.width,
      height=wrapper_to_find.height,
      query_radius=query_radius
    )
    if wrapper_to_find.original_path is not None:
      return find_similar_curves(wrapper_to_find=wrapper_to_find, wrappers_to_search=similar_height_width, max_dist=query_radius)
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
    total_dist += best_dist
    if max_dist >= 0 and total_dist > max_dist:
      # Return early
      return total_dist
  return total_dist

# TODO: Search for union of multiple wrappers_to_find
def find_similar_curves(
  wrapper_to_find: pdfextracter.LTJson,
  wrappers_to_search: typing.List[pdfextracter.LTJson],
  max_dist: float,
) -> typing.List[pdfextracter.LTJson]:
  lines_to_find = wrapper_to_find.get_zeroed_path_lines()
  if len(lines_to_find) == 0:
    return []

  results: typing.List[pdfextracter.LTJson] = []
  for wrapper in wrappers_to_search:
    potential_lines = wrapper.get_zeroed_path_lines()
    if len(potential_lines) == 0:
      continue
    if len(potential_lines) != len(lines_to_find):
      # TODO: Are they visually equivalent?
      continue
    dist = line_set_distance(lines1=lines_to_find, lines2=potential_lines, max_dist=max_dist)
    if dist < max_dist * len(potential_lines):
      results.append(wrapper)

  return results


def find_symbol_with_text(symbol: pdfextracter.LTJson, indexer: PdfIndexer):
  results = indexer.find_similar_shapes(wrapper_to_find=symbol, query_radius=1)
  result_inner_content: typing.List[pdfextracter.LTJson] = []
  for result in results:
    children = indexer.find_contains(bbox=result.bbox)
    char_children = [ c for c in children if c.size is not None]
    char_children.sort(key=lambda c: c.bbox[0])
    text = "".join([c.text for c in char_children if c.text is not None])
    result.label = text
    result_inner_content.extend(char_children)

  return results, result_inner_content