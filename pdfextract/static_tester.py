
import argparse
import typing
import time

import numpy as np
import pdfminer, pdfminer.layout, pdfminer.high_level

import pdfextracter
import pdftkdrawer

import scipy.spatial
import rtree

def text_is_window_key(text: str):
  if len(text) == 3 and text[0].isalpha() and text[1:].isdigit():
    return True
  return False

def extract_window_key(args):
  show_ui = True
  with np.load("../flaskapi/first_floor_construction.npz", allow_pickle=True) as f:
    page_elems, width, height = f["elems"], f["width"], f["height"]
    page_elems: typing.List[pdfminer.layout.LTComponent] = page_elems
    width = int(width)
    height = int(height)

  underlying_with_parent_idx = pdfextracter.get_underlying_parent_links(elems=page_elems)
  underlying = [u[0] for u in underlying_with_parent_idx]
  found_by_text = []
  for elem in underlying:
    if isinstance(elem, pdfminer.layout.LTText):
      text = elem.get_text()[:-1]
      if text_is_window_key(text):
        # LTTextBoxHorizontal contains a LTTextLineHorizontal both with the same text
        found_by_text.append(elem)

  def index_insertion_generator(elems: typing.List[pdfminer.layout.LTComponent]):
    for i, elem in enumerate(elems):
      x0, y0, x1, y1 = elem.bbox
      yield (i, (x0, height-y1, x1, height-y0), i)
  rtree_index = rtree.index.Index(index_insertion_generator(elems=underlying))
  y0, x0 = 1756, 1391
  y1, x1 = 1781, 1418
  found = rtree_index.intersection((x0, y0, x1, y1))
  q01_with_parent = [underlying_with_parent_idx[idx] for idx in found]
  q01_elems = [q[0] for q in q01_with_parent]
  q01_search_elems = q01_elems[1:2]
  search_elem = q01_search_elems[0]
  # all elements with same len(original_path) and similar shaped bbox
  # then break the original path into individual lines
  # then compare the lines
  # this will be a bit more difficult for bezier "c" paths
  # divide elements into len(original_path)
  # divide elements into bbox sizes/shapes

  elem_shapes = [[elem.width, elem.height] for elem in underlying]
  kdtree_index = scipy.spatial.KDTree(data=elem_shapes)
  search_elem_shape = [search_elem.width, search_elem.height]
  neighbor_idxes = kdtree_index.query_ball_point(x=search_elem_shape, r=1)
  neighbor_elems = [underlying_with_parent_idx[idx] for idx in neighbor_idxes]
  # TODO: Change draw_elems to highlight_elems, draw everything
  draw_elems = []
  window_keys_found = []
  for elem, elem_parent_idx in neighbor_elems:
    # TODO: Further filter elements that are the same type and path
    x0, y0, x1, y1 = elem.bbox
    content_bbox = (x0, height-y1, x1, height-y0)
    # Get contents of the same. Is it A## B## etc?
    neighbor_content_idxes = rtree_index.contains(content_bbox)
    neighbor_contents = [underlying_with_parent_idx[idx] for idx in neighbor_content_idxes]
    char_elems = [ n for n in neighbor_contents if isinstance(n[0], pdfminer.layout.LTChar)]
    char_elems.sort(key=lambda elem: elem[0].x0)
    text = "".join([c[0].get_text() for c in char_elems])
    if text == "5'-53":
      # Shape is close in size
      # print(elem, (elem.width, elem.height), search_elem_shape)
      pass

    if text_is_window_key(text=text):
      char_parent_idx = char_elems[0][1]
      if char_parent_idx is not None:
        char_parent = underlying[char_parent_idx]
        print((text, char_parent.get_text()[:-1]), ("Joined", "Container"), char_parent_idx)
      else:
        print(text, "No parent")
      draw_elems.extend([c[0] for c in char_elems])
      draw_elems.append(elem)
      window_keys_found.append(elem)

  # Match by text then search for the surrounding shape - works only if in text container and surrounding shape matches
  # Match by shape then search for text inside - works only if shape matches
  print("Count from shapes:", len(window_keys_found), "Count by text:", len(found_by_text)/2)

  if show_ui:
    drawer = pdftkdrawer.TkDrawer(width=width, height=height)
    drawer.draw_elems(elems=draw_elems)

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
