
import typing
import time

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level

import pdfextracter
import pdftkdrawer

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
    def index_insertion_generator(elems: typing.List[pdfextracter.LTWrapper]):
      for i, wrapper in enumerate(elems):
        elem = wrapper.elem
        x0, y0, x1, y1 = elem.bbox
        yield (i, (x0, page_height-y1, x1, page_height-y0), i)

    self.find_by_position_rtree = rtree.index.Index(index_insertion_generator(elems=wrappers))
    all_elem_shapes = [[wrapper.elem.width, wrapper.elem.height] for wrapper in wrappers]
    self.find_by_shape_kdtree = scipy.spatial.KDTree(data=all_elem_shapes)

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
  q01 = [elem_wrappers[idx].elem for idx in found]
  search_elem = q01[1]


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

  if show_ui:
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    drawer.draw_elems(elems=draw_wrappers)

    drawer.show("First floor construction plan")

def brute_force_find_contents(
  elem_wrappers: typing.List[pdfextracter.LTWrapper],
  bboxes: typing.List[typing.Tuple[float,float,float,float]],
):
  out: typing.List[pdfextracter.LTWrapper] = []
  for wrapper in elem_wrappers:
    elem = wrapper.elem
    bbox = elem.bbox
    for search_box in bboxes:
      if pdfextracter.box_contains(outer=search_box, inner=bbox):
        out.append(wrapper) # TODO: multiple boxes
  return out

def brute_force_find_shape(
  elem_wrappers: typing.List[pdfextracter.LTWrapper],
  shapes_hw: typing.List[typing.Tuple[float, float]],
):
  out: typing.List[pdfextracter.LTWrapper] = []
  for wrapper in elem_wrappers:
    elem = wrapper.elem
    for height, width in shapes_hw:
      diff = np.abs(height - elem.height) + np.abs(width - elem.width)
      if diff < 1:
        out.append(wrapper)
  return out

def kdtree_vs_brute_force():
  elem_wrappers, width, height = load_elems()

  find_width = 19.5
  find_height = 13.62
  i0 = time.time()
  # O(nlogn)
  indexer = PdfIndexer(wrappers=elem_wrappers, page_width=width, page_height=height)
  i1 = time.time()

  search_elem_shape = [find_width, find_height]
  # O(log(num_elements) * num_shapes_to_find)
  neighbor_idxes: typing.List[int] = indexer.find_by_shape_kdtree.query_ball_point(x=search_elem_shape, r=1) # type: ignore
  i2 = time.time()

  b0 = time.time()

  # O(num_elements * num_shapes_to_find)
  # 1000 * 1 vs 1000log(1000) + log(1000) * 1 = 6900
  # 1000 * 100 vs 1000log(1000) + log(1000) * 100 = 7600
  brute_results = brute_force_find_shape(elem_wrappers=elem_wrappers, shapes_hw=[(find_height, find_width)])
  b1 = time.time()

  print("Brute:", len(brute_results), b1-b0)
  print("TDTree:", len(neighbor_idxes), i1-i0, i2-i1)

  avg_num_elements_per_page = 43_000 * 10
  for num_shapes_to_find in range(1, 100):
    brute_force_O = avg_num_elements_per_page * num_shapes_to_find
    tdtree_O = avg_num_elements_per_page * np.log(avg_num_elements_per_page) + np.log(avg_num_elements_per_page) * num_shapes_to_find
    if tdtree_O < brute_force_O:
      # 11 shapes single page, 13 shapes 10 pages
      print("{0}: brute force {1} tdtree {2}".format(num_shapes_to_find, brute_force_O, tdtree_O))
      break

def load_elems():
  with np.load("../flaskapi/first_floor_construction.npz", allow_pickle=True) as f:
    page_elems, width, height = f["elems"], f["width"], f["height"]
    page_elems: typing.List[pdfminer.layout.LTComponent] = page_elems
    width = int(width)
    height = int(height)

  elem_wrappers = pdfextracter.get_underlying_parent_links(elems=page_elems)
  return elem_wrappers, width, height

def rtree_vs_brute_force():
  elem_wrappers, width, height = load_elems()

  y0, x0 = 1756, 1391
  y1, x1 = 1781, 1418
  bbox = (x0, y0, x1, y1)
  bbox_flipped = (x0, height-y1, x1, height-y0)

  for _ in range(1):
    tb0 = time.time()
    brute_force_result = brute_force_find_contents(elem_wrappers=elem_wrappers, bboxes=[bbox_flipped])
    tb1 = time.time()
    tr0 = time.time()
    indexer = PdfIndexer(wrappers=elem_wrappers, page_width=width, page_height=height)
    tr1 = time.time()
    rtree_result_idxes = indexer.find_by_position_rtree.contains(bbox) # type: ignore
    tr2 = time.time()
    rtree_result_idxes: typing.List[int] = list(rtree_result_idxes)
    tr3 = time.time()

    print("Brute force:", len(brute_force_result), tb1-tb0)
    print("rtree: {0} indexing time: {1} search time: {2} generator time: {3}".format(
      len(rtree_result_idxes),
      tr1-tr0,
      tr2-tr1,
      tr3-tr2,
    ))

def indexer_repeat_query_speed_test():
  elem_wrappers, width, height = load_elems()
  indexer = PdfIndexer(wrappers=elem_wrappers, page_width=width, page_height=height)
  y0, x0 = 1756, 1391
  y1, x1 = 1781, 1418

  times: typing.List[typing.Tuple[float, float]] = []
  for _ in range(5):
    t0 = time.time()
    res_rtree = indexer.find_by_position_rtree.intersection((x0, y0, x1, y1))
    res_rtree = list(res_rtree)
    t1 = time.time()
    find_width = 19.5
    find_height = 13.62
    search_elem_shape = [find_width, find_height]
    t2 = time.time()
    res_kdtree = indexer.find_by_shape_kdtree.query_ball_point(x=search_elem_shape, r=1) # type: ignore
    t3 = time.time()
    times.append((t1-t0, t3-t2))
    if len(res_rtree) == 0 or len(res_kdtree) == 0:
      print(len(res_rtree), len(res_kdtree))
      print("No results found")
  print(times)


def main():
  kdtree_vs_brute_force()
  rtree_vs_brute_force()
  indexer_repeat_query_speed_test()

if __name__ == "__main__":
  main()
