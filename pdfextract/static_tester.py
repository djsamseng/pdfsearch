
import argparse
import typing

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils

import pdfextracter
import pdftkdrawer
import path_utils

import scipy.spatial # type: ignore
import rtree

def text_is_window_key(text: str):
  if len(text) == 3 and text[0].isalpha() and text[1:].isdigit():
    return True
  return False



class PdfIndexer:
  # To find contents inside shapes
  find_by_position_rtree: rtree.index.Index
  # To find similar shapes
  find_by_shape_kdtree: scipy.spatial.KDTree
  def __init__(
    self,
    wrappers: typing.List[pdfextracter.LTWrapper],
    page_width: int,
    page_height: int,
  ) -> None:
    self.page_width = page_width
    self.page_height = page_height
    self.wrappers = wrappers
    def index_insertion_generator(elems: typing.List[pdfextracter.LTWrapper]):
      for i, wrapper in enumerate(elems):
        elem = wrapper.elem
        yield (i, elem.bbox, i)

    self.find_by_position_rtree = rtree.index.Index(index_insertion_generator(elems=wrappers))
    all_elem_shapes = [[wrapper.elem.width, wrapper.elem.height] for wrapper in wrappers]
    self.find_by_shape_kdtree = scipy.spatial.KDTree(data=all_elem_shapes)

  def find_contains(
    self,
    bbox: typing.Tuple[float, float, float, float],
    y_is_down: bool = False,
  ) -> typing.List[pdfextracter.LTWrapper]:
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
  ) -> typing.List[pdfextracter.LTWrapper]:
    search_shape = [width, height]
    result_idxes: typing.List[int] = self.find_by_shape_kdtree.query_ball_point(x=search_shape, r=query_radius) # type: ignore
    results = [self.wrappers[idx] for idx in result_idxes]
    return results

  def find_similar_shapes(
    self,
    wrapper_to_find: pdfextracter.LTWrapper,
    query_radius: float,
  ) -> typing.List[pdfextracter.LTWrapper]:
    similar_height_width = self.find_similar_height_width(
      width=wrapper_to_find.elem.width,
      height=wrapper_to_find.elem.height,
      query_radius=query_radius
    )
    elem = wrapper_to_find.elem
    if isinstance(elem, pdfminer.layout.LTCurve):
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
  wrapper_to_find: pdfextracter.LTWrapper,
  wrappers_to_search: typing.List[pdfextracter.LTWrapper],
  max_dist: float,
) -> typing.List[pdfextracter.LTWrapper]:
  lines_to_find = wrapper_to_find.get_zeroed_path_lines()
  if len(lines_to_find) == 0:
    return []

  results: typing.List[pdfextracter.LTWrapper] = []
  for wrapper in wrappers_to_search:
    potential_lines = wrapper.get_zeroed_path_lines()
    if len(potential_lines) == 0:
      continue
    if len(potential_lines) != len(lines_to_find):
      # TODO: Are they visually equivalent?
      continue
    dist = line_set_distance(lines1=lines_to_find, lines2=potential_lines, max_dist=max_dist)
    if dist < max_dist:
      results.append(wrapper)

  return results


def find_similar(
  indexer: PdfIndexer,
  search_shape: pdfextracter.LTWrapper,
  inner_text_matcher: typing.Callable[[str], bool]
):
  # all elements with similar shaped bbox


  # same len(original_path)
  # then break the original path into individual lines
  # then compare the lines
  # this will be a bit more difficult for bezier "c" paths

  # then match inner text, organize by inner text
  pass

def extract_window_key(args: typing.Any):
  show_ui = True
  with np.load("../flaskapi/first_floor_construction.npz", allow_pickle=True) as f:
    page_elems, width, height = f["elems"], f["width"], f["height"]
    page_elems: typing.List[pdfminer.layout.LTComponent] = page_elems
    width = int(width)
    height = int(height)

  elem_wrappers = pdfextracter.get_underlying_parent_links(elems=page_elems)
  found_by_text: typing.List[pdfextracter.LTWrapper] = []
  for wrapper in elem_wrappers:
    elem = wrapper.elem
    if isinstance(elem, pdfminer.layout.LTText):
      text = elem.get_text()[:-1]
      if text_is_window_key(text):
        # LTTextBoxHorizontal contains a LTTextLineHorizontal both with the same text
        found_by_text.append(wrapper)

  def index_insertion_generator(elems: typing.List[pdfextracter.LTWrapper]):
    for i, wrapper in enumerate(elems):
      elem = wrapper.elem
      x0, y0, x1, y1 = elem.bbox
      yield (i, (x0, height-y1, x1, height-y0), i)
  rtree_index = rtree.index.Index(index_insertion_generator(elems=elem_wrappers))
  y0, x0 = 1756, 1391
  y1, x1 = 1781, 1418
  found = rtree_index.intersection((x0, y0, x1, y1))
  q01 = [elem_wrappers[idx] for idx in found]
  search_wrapper = q01[1]
  search_elem = search_wrapper.elem


  all_elem_shapes = [[wrapper.elem.width, wrapper.elem.height] for wrapper in elem_wrappers]
  kdtree_index = scipy.spatial.KDTree(data=all_elem_shapes)
  search_elem_shape = [search_elem.width, search_elem.height]
  neighbor_idxes: typing.List[int] = kdtree_index.query_ball_point(x=search_elem_shape, r=1) # type: ignore
  neighbor_wrappers = [elem_wrappers[idx] for idx in neighbor_idxes]
  # TODO: Change draw_elems to highlight_elems, draw everything
  draw_wrappers: typing.List[pdfextracter.LTWrapper] = []
  for wrapper in neighbor_wrappers:
    elem = wrapper.elem
    # elem = thing of similar shape
    # TODO: Further filter elements that are the same type and path
    x0, y0, x1, y1 = elem.bbox
    content_bbox = (x0, height-y1, x1, height-y0)
    # Get contents of the same. Is it A## B## etc?
    neighbor_content_idxes = rtree_index.contains(content_bbox)
    if neighbor_content_idxes is not None:
      neighbor_contents = [elem_wrappers[idx] for idx in neighbor_content_idxes]
      char_wrappers = [ n for n in neighbor_contents if isinstance(n.elem, pdfminer.layout.LTChar)]
      char_wrappers.sort(key=lambda wrapper: wrapper.elem.x0)
      text = "".join([typing.cast(pdfminer.layout.LTText, wrapper.elem).get_text() for wrapper in char_wrappers])
      if text == "5'-53":
        # Shape is close in size
        # print(elem, (elem.width, elem.height), search_elem_shape)
        pass

      if text_is_window_key(text=text):
        char_parent_idx = char_wrappers[0].parent_idx
        if char_parent_idx is not None:
          char_parent = elem_wrappers[char_parent_idx].elem
          if isinstance(char_parent, pdfminer.layout.LTText):
            print((text, char_parent.get_text()[:-1]), ("Joined", "Container"), char_parent_idx)
          else:
            print(text, "Parent not text")
        else:
          print(text, "No parent")
        # Draw what is inside the shape
        draw_wrappers.extend(char_wrappers)
        # Draw the shape
        draw_wrappers.append(wrapper)

  # Match by text then search for the surrounding shape - works only if in text container and surrounding shape matches
  # Match by shape then search for text inside - works only if shape matches
  print("Count from shapes:", len(draw_wrappers), "Count by text:", len(found_by_text)/2)

  indexer = PdfIndexer(wrappers=elem_wrappers, page_width=width, page_height=height)
  indexer_found_shapes = indexer.find_similar_shapes(wrapper_to_find=search_wrapper, query_radius=1)
  print("Count from indexer no text:", len(indexer_found_shapes))
  if show_ui:
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    drawer.draw_elems(elems=indexer_found_shapes)

    drawer.show("First floor construction plan")

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--awindows", dest="awindows", default=False, action="store_true")
  return parser.parse_args()

def main():
  args = parse_args()
  extract_window_key(args)

if __name__ == "__main__":
  main()
