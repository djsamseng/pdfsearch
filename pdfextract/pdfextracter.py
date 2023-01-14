

import typing
import re

from . import pdfindexer

def extract_page_name(indexer: pdfindexer.PdfIndexer):
  orig_height = 2160
  orig_width = 3024
  y0, x0 = 1872, 2773
  # y1, x1 = 2111, 2975
  w = orig_width-x0
  h = orig_height-y0
  # y0a, x0 = 1438, 2339
  # y1a, x1 = 1681, 2544

  # Scaling fails - need to find the box surrounding

  bbox=(indexer.page_width-w, indexer.page_height-h, indexer.page_width, indexer.page_height)
  results = indexer.find_contains(bbox=bbox, y_is_down=True)
  containers = [r for r in results if r.is_container]
  no_parent = [c for c in containers if c.parent_idx is None]

  no_parent.sort(key=lambda c: c.bbox[1], reverse=True)

  page_key_regex = re.compile("[a-zA-Z]-\\d")
  def is_page_name(text: typing.Union[None, str]):
    if text is None:
      return False
    lower = text.lower().replace("\n", "")
    if page_key_regex.search(lower) is not None:
      return False
    if lower in set(["drawing title", "drawing number"]):
      return False
    return True
  name_elems = [c for c in no_parent if is_page_name(c.text)]
  return " ".join([c.text for c in name_elems if c.text is not None]).strip().strip("\n").replace("\n", " ")

