
import argparse
import typing

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils
import rtree
import scipy.spatial # type: ignore

from . import pdfextracter
from . import pdfindexer
from . import pdftkdrawer

def text_is_window_key(text: str):
  if len(text) == 3 and text[0].isalpha() and text[1:].isdigit():
    return True
  return False

def find_similar(
  indexer: pdfindexer.PdfIndexer,
  search_shape: pdfextracter.LTJson,
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
  found_by_text: typing.List[pdfextracter.LTJson] = []
  for wrapper in elem_wrappers:
    if wrapper.text is not None:
      text = wrapper.text[:-1]
      if text_is_window_key(text):
        # LTTextBoxHorizontal contains a LTTextLineHorizontal both with the same text
        found_by_text.append(wrapper)

  def index_insertion_generator(elems: typing.List[pdfextracter.LTJson]):
    for i, wrapper in enumerate(elems):
      x0, y0, x1, y1 = wrapper.bbox
      yield (i, (x0, height-y1, x1, height-y0), i)
  rtree_index = rtree.index.Index(index_insertion_generator(elems=elem_wrappers))
  y0, x0 = 1756, 1391
  y1, x1 = 1781, 1418
  found = rtree_index.intersection((x0, y0, x1, y1))
  q01 = [elem_wrappers[idx] for idx in found]
  search_wrapper = q01[1]


  all_elem_shapes = [[wrapper.width, wrapper.height] for wrapper in elem_wrappers]
  kdtree_index = scipy.spatial.KDTree(data=all_elem_shapes)
  search_elem_shape = [search_wrapper.width, search_wrapper.height]
  neighbor_idxes: typing.List[int] = kdtree_index.query_ball_point(x=search_elem_shape, r=1) # type: ignore
  neighbor_wrappers = [elem_wrappers[idx] for idx in neighbor_idxes]
  # TODO: Change draw_elems to highlight_elems, draw everything
  draw_wrappers: typing.List[pdfextracter.LTJson] = []
  for wrapper in neighbor_wrappers:
    # elem = thing of similar shape
    # TODO: Further filter elements that are the same type and path
    x0, y0, x1, y1 = wrapper.bbox
    content_bbox = (x0, height-y1, x1, height-y0)
    # Get contents of the same. Is it A## B## etc?
    neighbor_content_idxes = rtree_index.contains(content_bbox)
    if neighbor_content_idxes is not None:
      neighbor_contents = [elem_wrappers[idx] for idx in neighbor_content_idxes]
      char_wrappers = [ n for n in neighbor_contents if n.size is not None]
      char_wrappers.sort(key=lambda wrapper: wrapper.bbox[0])
      text = "".join([wrapper.text for wrapper in char_wrappers if wrapper.text is not None])
      if text == "5'-53":
        # Shape is close in size
        # print(elem, (elem.width, elem.height), search_elem_shape)
        pass

      if text_is_window_key(text=text):
        char_parent_idx = char_wrappers[0].parent_idx
        if char_parent_idx is not None:
          char_parent = elem_wrappers[char_parent_idx]
          if char_parent.text is not None:
            print((text, char_parent.text[:-1]), ("Joined", "Container"), char_parent_idx)
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

  indexer = pdfindexer.PdfIndexer(wrappers=elem_wrappers, page_width=width, page_height=height)
  indexer_found_shapes = indexer.find_similar_shapes(wrapper_to_find=search_wrapper, query_radius=1)
  print("Count from indexer no text:", len(indexer_found_shapes))
  if show_ui:
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    drawer.draw_elems(elems=indexer_found_shapes)

    drawer.show("First floor construction plan")

def extract_first_floor():
  import time
  page_gen = pdfminer.high_level.extract_pages(pdf_file="plan.pdf", page_numbers=[6,7,8,9])
  for _, page in enumerate(page_gen):
    tp0 = time.time()
    elems = pdfextracter.get_underlying_parent_links(elems=page)
    tp1 = time.time()

    # extracting the page in enumerate(page_gen) takes the most time
    print("Took:", tp1-tp0, time.time()-tp0)
  return
  y0a, x0 = 1873, 2772
  y1a, x1 = 2113, 2977

  y0 = height - y1a
  y1 = height - y0a
  results = pdfextracter.filter_contains_bbox_hierarchical(elems=elems, bbox=(x0,y0,x1,y1))
  char_results = [r for r in results if r.size is not None]
  containers = [r for r in results if r.is_container]
  for parent in containers:
    # TODO: set child idxes?
    print(parent.text, "x,y=", parent.bbox[0], parent.bbox[1])
  print(len(results), len(char_results), len(containers))
  return


  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=elems, draw_buttons=False)
  drawer.show("First Floor")

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--awindows", dest="awindows", default=False, action="store_true")
  return parser.parse_args()

def main():
  args = parse_args() # type: ignore
  #extract_window_key(args)
  extract_first_floor()

if __name__ == "__main__":
  # python3 -m pdfextract.static_tester
  main()
