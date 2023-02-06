
import collections
import typing
import re

import rtree

from . import pdfindexer, pdfelemtransforms
from .ltjson import LTJson, BboxType

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

def is_line_vertical(elem: LTJson):
  x0, y0, x1, y1 = elem.bbox
  dx = abs(x1-x0)
  dy = abs(y1-y0)
  if dx <= 1 and dy/(dx+0.1) > 0.9:
    return True
  return False
def is_line_horizontal(elem: LTJson):
  x0, y0, x1, y1 = elem.bbox
  dx = abs(x1-x0)
  dy = abs(y1-y0)
  if dy <= 1 and dy/(dx+0.1) < 0.1:
    return True
  return False

def remove_duplicate_bbox_text(items: typing.List[LTJson]):
  def item_size(item: LTJson):
    x0, y0, x1, y1 = item.bbox
    return (x1-x0) * (y1-y0)
  items.sort(key=lambda x: item_size(x), reverse=True) # pylint:disable=unnecessary-lambda

  bbox_indexer = rtree.index.Index()
  out: typing.List[LTJson] = []
  idx = 0
  radius = 0
  for item in items:
    results = bbox_indexer.intersection(item.bbox)
    if item.text is None or results is None or len(list(results)) == 0:
      x0, y0, x1, y1 = item.bbox
      bbox = (x0-radius, y0-radius, x1+radius, y1+radius)
      if item.text is None:
        bbox_indexer.insert(idx, (-1,-1,-1,-1))
      else:
        bbox_indexer.insert(idx, bbox)
      out.append(item)
      idx += 1
  return out

class ExtractedRowElem():
  def __init__(self, text:str, elems: typing.List[LTJson], bbox: BboxType) -> None:
    self.text = text
    self.elems = elems
    self.bbox = bbox

def elem_splits_another_elem(elem_idx: int, others: typing.List[LTJson]) -> bool:
  for other_idx in range(len(others)):
    if elem_idx == other_idx:
      continue
    my_top_below_your_top = elem.bbox[3] < other.bbox[3]
  return True
  for other in others:
    my_top_below_your_top = elem.bbox[3] < other.bbox[3] - padding
    my_top_above_your_bottom = elem.bbox[3] > other.bbox[1] + padding
    if my_top_below_your_top and my_top_above_your_bottom:
      return False
  return True

def vertical_aligns(e1: LTJson, e2: LTJson) -> bool:
  return e1.bbox[3] >= e2.bbox[1] and e1.bbox[1] <= e2.bbox[3]

def vertical_aligns_others(elem: LTJson, others: typing.List[LTJson]) -> typing.Union[None, int]:
  for idx, other in enumerate(others):
    if vertical_aligns(e1=elem, e2=other):
      return idx
  return None

def get_line_splits(elems: typing.List[LTJson]) -> typing.List[float]:
  cur_tops: typing.List[LTJson] = []
  for consider in elems:
    vertical_collision_idx = vertical_aligns_others(elem=consider, others=cur_tops)
    if vertical_collision_idx is not None:
      vertical_collision = cur_tops[vertical_collision_idx]
      if vertical_collision.bbox[3] < consider.bbox[3]:
        cur_tops[vertical_collision_idx] = consider
    else:
      cur_tops.append(consider)
  return [top.bbox[3] for top in cur_tops]

def join_line_split(elems: typing.List[LTJson]) -> str:
  out = ""
  has_no_text = True
  if len(elems) > 0 and elems[0].text is not None:
    out += elems[0].text
    has_no_text = False
  for idx in range(1, len(elems)):
    last_elem = elems[idx-1]
    elem = elems[idx]
    elem_width = max(elem.bbox[2]-elem.bbox[0], last_elem.bbox[2]-last_elem.bbox[0])
    x_space = elem.bbox[0] - last_elem.bbox[2]
    if x_space > 0.5 * elem_width:
      out += ""
    if elem.text is None:
      # TODO: other kinds of shapes
      out += "/"
    else:
      out += elem.text
      has_no_text = False
  if has_no_text:
    return ""
  return out

def join_text(elems: typing.List[LTJson]) -> str:
  text_line_tops = get_line_splits(elems=elems)
  text_line_tops.sort()
  text_lines: typing.List[typing.List[LTJson]] = [[] for _ in range(len(text_line_tops))]
  for elem in elems:
    for text_line_idx in range(len(text_lines)):
      if elem.bbox[3] <= text_line_tops[text_line_idx]:
        text_lines[text_line_idx].append(elem)
        break

  for text_line in text_lines:
    text_line.sort(key=lambda e:e.bbox[0]) # left right
  text_lines.sort(key=lambda line_elems: line_elems[0].bbox[3], reverse=True) # top down
  text = " ".join([join_line_split(text_line) for text_line in text_lines])
  return text

def extract_row(
  table_elems: typing.List[LTJson],
  bbox: pdfelemtransforms.BboxType,
  vertical_dividers: typing.List[LTJson],
  padding: float
):
  bbox = (
    bbox[0] + padding,
    bbox[1] + padding,
    bbox[2] - padding,
    bbox[3] - padding,
  )
  elems_in_row = [
    e for e in table_elems if \
      pdfelemtransforms.box_contains(outer=bbox, inner=e.bbox) and not e.is_container
  ]
  elems_in_row.sort(key=lambda e: e.bbox[2]) # left to right by their right side
  vertical_divider_bboxes = [ (bbox[0], bbox[1], bbox[0], bbox[3]) ] # left/begin
  vertical_divider_bboxes.extend([ v.bbox for v in vertical_dividers ]) # middle
  vertical_divider_bboxes.append( (bbox[2],bbox[1],bbox[2],bbox[3]) ) # right/end
  vertical_divider_bboxes.sort(key=lambda v: v[0]) # left to right
  row: typing.List[ExtractedRowElem] = []
  # If multicolumn, join MATERIAL INT = column 0, MATERIAL EXT = column 1
  elem_idx = 0
  for divider_idx in range(1, len(vertical_divider_bboxes)):
    left_divider = vertical_divider_bboxes[divider_idx - 1]
    right_divider = vertical_divider_bboxes[divider_idx]
    elems_in_this_box: typing.List[LTJson] = []
    while elem_idx < len(elems_in_row) and \
      elems_in_row[elem_idx].bbox[2] < right_divider[0]:

      add_elem = elems_in_row[elem_idx]
      elems_in_this_box.append(add_elem)
      elem_idx += 1

    cell_bbox = (
      left_divider[0],
      left_divider[1],
      right_divider[2],
      right_divider[3],
    )
    row_text = join_text(elems=elems_in_this_box)
    row.append(ExtractedRowElem(text=row_text, elems=elems_in_this_box, bbox=cell_bbox))

  return row

def extract_table(
  indexer: pdfindexer.PdfIndexer,
  text_key: str,
  has_header: bool,
  header_above_table: bool,
):
  table_padding = 0.1
  lookup_results = indexer.text_lookup[text_key]
  if len(lookup_results) == 0:
    return None, None
  key_elem = lookup_results[0]
  x0, y0, x1, _ = key_elem.bbox
  # Find the rect that contains the table
  below = indexer.find_top_left_in(bbox=(x0-key_elem.height*2, y0-key_elem.height*4, x1, y0))
  rects = [ b for b in below if b.is_rect ]
  # Take the biggest rect
  table_rect_item: LTJson = max(rects, key=lambda x: x.width * x.height)
  # Find everything inside the table rect
  if header_above_table:
    header_bbox = (
      table_rect_item.bbox[0],
      table_rect_item.bbox[3],
      table_rect_item.bbox[2],
      key_elem.bbox[1]
    )
    table_rect = (
      table_rect_item.bbox[0],
      table_rect_item.bbox[1],
      table_rect_item.bbox[2],
      key_elem.bbox[1],
    )
  else:
    table_rect = table_rect_item.bbox
  inside_schedule = indexer.find_contains(bbox=table_rect)
  # Get horizontal lines that start at the left
  def is_left_aligned(elem: LTJson):
    return elem.bbox[0] <= table_rect[0] + 10
  left_aligned_horizontal_lines = [
    s for s in inside_schedule if is_left_aligned(s) and is_line_horizontal(s)
  ]
  # sort them vertically top down
  left_aligned_horizontal_lines.sort(key=lambda s: s.bbox[3], reverse=True)
  if header_above_table:
    # Already set header_bbox
    header_bbox = typing.cast(pdfelemtransforms.BboxType, header_bbox) # type:ignore
  elif has_header:
    header_content_min_height = 5
    header_line = next(
      (x for x in left_aligned_horizontal_lines if \
        x.bbox[3] < table_rect[3] - header_content_min_height),
      None
    )
    if header_line is None:
      return None, None
    header_bbox = (
      header_line.bbox[0],
      header_line.bbox[1],
      header_line.bbox[2],
      table_rect[3],
    )
  else:
    header_bbox = (
      table_rect[0],
      table_rect[3],
      table_rect[2],
      table_rect[3],
    )

  vertical_dividers = [
    s for s in inside_schedule if \
      s.bbox[1] >= table_rect[1] and s.bbox[3] >= header_bbox[1] and \
      is_line_vertical(s)
  ]
  for v in vertical_dividers:
    v.bbox = (v.bbox[0], v.bbox[1], v.bbox[2], key_elem.bbox[1])
  # Follow those vertical lines down until the first one ends
  vertical_divider_bottom = max([s.bbox[1] for s in vertical_dividers])
  # At this point we should see a horizontal line that reaches full width and ends the table
  header_row = extract_row(
    table_elems=inside_schedule,
    bbox=header_bbox,
    vertical_dividers=vertical_dividers,
    padding=table_padding
  )

  rows: typing.List[typing.List[ExtractedRowElem]] = []
  for bottom_divider_idx in range(1, len(left_aligned_horizontal_lines)):
    bottom_divider = left_aligned_horizontal_lines[bottom_divider_idx]
    top_divider = left_aligned_horizontal_lines[bottom_divider_idx - 1]
    if bottom_divider.bbox[3] >= header_bbox[1]:
      continue
    if top_divider.bbox[3] <= vertical_divider_bottom:
      break
    row = extract_row(
      table_elems=inside_schedule,
      bbox=(
        top_divider.bbox[0],
        bottom_divider.bbox[1],
        top_divider.bbox[2],
        top_divider.bbox[3]
      ),
      vertical_dividers=vertical_dividers,
      padding=table_padding
    )
    rows.append(row)

  return header_row, rows
