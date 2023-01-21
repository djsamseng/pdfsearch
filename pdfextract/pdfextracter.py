

import typing
import re

from . import pdfindexer
from .ltjson import LTJson

def extract_page_name(indexer: pdfindexer.PdfIndexer):
  orig_height = 2160
  orig_width = 3024
  # python3 -m pdfextract.michaelsmithsymbols --showall
  # TODO: Locate DRAWING TITLE. Then get the box. Then get the boxes content
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

def extract_house_name(
  regex: re.Pattern, # type: ignore
  elem: LTJson,
  indexer: pdfindexer.PdfIndexer
):
  if elem.text is None:
    return None
  match = regex.search(elem.text.lower())
  if match is None:
    return None
  if elem.bbox[0] / indexer.page_width < 0.8:
    # print("Left too much")
    return None
  if elem.bbox[1] / indexer.page_height > 0.4:
    # print("Up too much")
    return None
  x0, y0, _, _ = elem.bbox
  bbox = (x0-10, 0, indexer.page_width, y0)
  nearby = indexer.find_contains(bbox=bbox, y_is_down=False)
  containers = [r for r in nearby if r.is_container]
  no_parent = [c for c in containers if c.parent_idx is None]

  no_parent.sort(key=lambda c: c.bbox[1], reverse=True)
  project_name_parts: typing.List[str] = []
  has_drawing_title = False
  for item in no_parent:
    if item.text and item.text.lower().find("drawing title") >= 0:
      has_drawing_title = True

  for idx, item in enumerate(no_parent):
    if item.text is None:
      continue
    if item.text.lower().find("drawing title") >= 0:
      break
    if not has_drawing_title and idx >= 3:
      break
    if item.text.lower().find("owner") == 0:
      continue
    project_name_parts.append(item.text.replace("\n", " "))

  joined = "".join(project_name_parts).strip()
  return joined
