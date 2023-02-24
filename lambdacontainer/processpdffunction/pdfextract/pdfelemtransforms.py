
import enum
import math
import json
import typing

import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils

from . import pdftypes, path_utils
from .ltjson import LTJson, BboxType, LTJsonEncoder

def get_underlying_parent_links_impl(
  out: typing.List[LTJson],
  elem: pdfminer.layout.LTComponent,
  elem_parent_idx: typing.Union[None, int],
):
  add_containers = False
  if isinstance(elem, pdfminer.layout.LTContainer):
    if not add_containers:
      print("Container found: Was .local/lib/python3.8/site-packages/pdfminer/layout.py line 959 def analyze to return early?")
    child_parent_idx = None
    if add_containers:
      out.append(
        LTJson(
          elem=typing.cast(pdfminer.layout.LTComponent, elem),
          parent_idx=elem_parent_idx
        )
      )
      if isinstance(elem, pdfminer.layout.LTText):
        # takes 20ms out of 150ms
        text = elem.get_text()
        out[-1].text = text
      child_parent_idx = len(out) - 1 # Get the container's idx
    for child in typing.cast(typing.Iterable[pdfminer.layout.LTComponent], elem):
      # Add the first child
      # Get the first child's idx
      # Add the first child's children - recurse
      get_underlying_parent_links_impl(out=out, elem=child, elem_parent_idx=child_parent_idx)
  elif isinstance(elem, pdfminer.layout.LTChar):
    if add_containers and elem_parent_idx is None:
      print("LTChar without parent:", elem, elem_parent_idx)
    out.append(LTJson(elem, parent_idx=elem_parent_idx))
  elif isinstance(elem, pdfminer.layout.LTAnno):
    text = elem.get_text()
    if text != "\n" and text != " ":
      print("Unhandled LTAnno", elem)
    # Not Added
  elif isinstance(elem, pdfminer.layout.LTCurve):
    out.append(LTJson(elem, parent_idx=elem_parent_idx))
  elif isinstance(elem, pdfminer.layout.LTFigure):
    # Not Added
    print("Unhandled figure", elem)
  elif isinstance(elem, pdfminer.layout.LTImage):
    # TODO: Notify user pdf images not searched
    pass
  else:
    print("Unhandled elem:", elem)

def get_underlying_parent_links(
  elems: typing.Iterable[pdfminer.layout.LTComponent],
):
  out: typing.List[LTJson] = []
  for elem in elems:
    get_underlying_parent_links_impl(out=out, elem=elem, elem_parent_idx=None)
  return out

def box_contains(outer: BboxType, inner: BboxType):
  x0a, y0a, x1a, y1a = outer
  x0b, y0b, x1b, y1b = inner
  if x0a <= x0b and y0a <= y0b:
    # outer starts before inner
    if x1a >= x1b and y1a >= y1b:
      # outer ends after inner
      return True
  return False

def boundaries_contains(
  boundaries: typing.List[
    typing.Union[None, pdftypes.ClassificationNode]
  ],
  bbox: pdftypes.Bbox,
):
  for idx in range(len(bbox)):
    boundary_elem = boundaries[idx]
    if boundary_elem is not None:
      if idx < 2:
        if bbox[idx] < boundary_elem.bbox[idx]:
          return False
      else:
        if bbox[idx] > boundary_elem.bbox[idx]:
          return False
  return True

def filter_contains_bbox_hierarchical(elems: typing.Iterable[LTJson], bbox: BboxType) -> typing.List[LTJson]:
  out: typing.List[LTJson] = []
  json_encoder = LTJsonEncoder()
  old_idx_to_new_idx: typing.Dict[int, int] = dict()
  for old_idx, wrapper in enumerate(elems):
    new_parent_idx = None
    if wrapper.parent_idx is not None:
      if wrapper.parent_idx in old_idx_to_new_idx:
        new_parent_idx = old_idx_to_new_idx[wrapper.parent_idx]
    if wrapper.is_annotation:
      continue
    if box_contains(outer=bbox, inner=wrapper.bbox):
      elem_copy = LTJson(serialized_json=json.loads(json_encoder.encode(wrapper)))
      elem_copy.parent_idx = new_parent_idx
      out.append(elem_copy)
      old_idx_to_new_idx[old_idx] = len(out) - 1

  return out

class LineType(enum.Enum):
  VERT = 1
  HORIZ = 2
  NONE = 3

def is_line(a: BboxType):
  x0, y0, x1, y1 = a
  if x1-x0 < 0.1:
    if y1-y0 > 0.1:
      return LineType.VERT
  if y1 - y0 < 0.1:
    if x1 - x0 > 0.1:
      return LineType.HORIZ
  return LineType.NONE

def bbox_intersection_area(a: BboxType, b: BboxType):
  a_top = max(a[1], a[3])
  a_bottom = min(a[1], a[3])
  b_top = max(b[1], b[3])
  b_bottom = min(b[1], b[3])

  left = max(a[0], b[0])
  right = min(a[2], b[2])
  bottom = max(a_bottom, b_bottom)
  top = min(a_top, b_top)

  if left < right and bottom < top:
    return (right - left) * (top - bottom)
  elif left == right:
    return 0.1 * (top - bottom)
  elif bottom == top:
    return (right - left) * 0.1
  return 0

def get_distance_between(
  this: typing.Union[pdftypes.Bbox, path_utils.LinePointsType],
  other: typing.Union[pdftypes.Bbox, path_utils.LinePointsType],
  vert: bool
):
  idx0, idx1 = get_idx_for_vert(vert=vert)
  selfmin = min(this[idx0], this[idx1])
  selfmax = max(this[idx0], this[idx1])
  othermin = min(other[idx0], other[idx1])
  othermax = max(other[idx0], other[idx1])
  if selfmin >= othermax:
    return selfmin - othermax
  elif othermin >= selfmax:
    return othermin - selfmax
  else:
    return 0

def get_distance_to(
  src: typing.Union[pdftypes.Bbox, path_utils.LinePointsType],
  other: typing.Union[pdftypes.Bbox, path_utils.LinePointsType],
):
  vert_distance = get_distance_between(
    this=src,
    other=other,
    vert=True
  )
  horiz_distance = get_distance_between(
    this=src,
    other=other,
    vert=False
  )
  return math.sqrt(vert_distance ** 2 + horiz_distance ** 2)

def get_node_distance_to(
  other: pdftypes.ClassificationNode,
  src: pdftypes.ClassificationNode,
):
  return get_distance_to(src=src.bbox, other=other.bbox)

def get_midpoint(item: typing.Union[pdftypes.Bbox, path_utils.LinePointsType]):
  x0, y0, x1, y1 = item
  xmid = abs(x1 - x0) / 2 + min(x0, x1)
  ymid = abs(y1 - y0) / 2 + min(y0, y1)
  return xmid, ymid

def get_quad(dx: float, dy: float):
  if dx >= 0 and dy >= 0:
    return 0
  if dx >= 0 and dy < 0:
    return 1
  if dx < 0 and dy < 0:
    return 2
  if dx < 0 and dy >= 0:
    return 3
  raise ValueError("Unhandled dx{0} dy{1}".format(dx, dy))

def get_angle(dx: float, dy: float):
  # Top = 0
  # Left = -90
  # Right = 90
  # bottom = -179, 180, 179
  angle = math.degrees(math.atan2(dx, dy))
  return angle

def get_node_angle_to(
  other: pdftypes.ClassificationNode,
  src: pdftypes.ClassificationNode,
):
  if src.line is not None:
    src_x, src_y = get_midpoint(item=src.line)
  else:
    src_x, src_y = get_midpoint(item=src.bbox)
  if other.line is not None:
    other_x, other_y = get_midpoint(item=other.line)
  else:
    other_x, other_y = get_midpoint(item=other.bbox)
  dx, dy = other_x - src_x, other_y - src_y
  angle = get_angle(dx=dx, dy=dy)
  return angle

def get_node_points(node: pdftypes.ClassificationNode):
  if node.line is not None:
    x0, y0, x1, y1 = node.line
    pts = ((x0, y0), (x0, y0), (x1, y1), (x1, y1))
  else:
    x0, y0, x1, y1 = node.bbox
    pts = ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
  return pts

def get_node_angles_to(
  other: pdftypes.ClassificationNode,
  src: pdftypes.ClassificationNode
):
  other_pts = get_node_points(node=other)
  src_pts =  get_node_points(node=src)
  angles: typing.List[float] = []
  for idx in range(len(other_pts)):
    dx = other_pts[idx][0] - src_pts[idx][0]
    dy = other_pts[idx][1] - src_pts[idx][1]
    angle =  get_angle(dx=dx, dy=dy)
    angles.append(angle)
  return angles

def get_node_directions_to(
  other: pdftypes.ClassificationNode,
  src: pdftypes.ClassificationNode,
):
  pass

def get_idx_for_vert(vert: bool):
  if vert:
    idx0 = 1
    idx1 = 3
  else:
    idx0 = 0
    idx1 = 2
  return idx0, idx1

def other_is_pos_gte(selfmin: float, selfmax: float, othermin:float, othermax: float):
  if othermin >= selfmax:
    return True
  if othermin >= selfmin and othermax >= selfmax:
    return True
  return False

def other_is_pos_lte(selfmin: float, selfmax: float, othermin:float, othermax: float):
  if othermax <= selfmin:
    return True
  if othermax <= selfmax and othermin <= selfmin:
    return True
  return False

def other_is_pos_gte_this(
  this: typing.Union[pdftypes.Bbox, path_utils.LinePointsType],
  other: typing.Union[pdftypes.Bbox, path_utils.LinePointsType],
  vert: bool,
  above: bool,
):
  idx0, idx1 = get_idx_for_vert(vert=vert)
  selfmin = min(this[idx0], this[idx1])
  selfmax = max(this[idx0], this[idx1])
  othermin = min(other[idx0], other[idx1])
  othermax = max(other[idx0], other[idx1])
  if above:
    return other_is_pos_gte(selfmin=selfmin, selfmax=selfmax, othermin=othermin, othermax=othermax)
  else:
    return other_is_pos_lte(selfmin=selfmin, selfmax=selfmax, othermin=othermin, othermax=othermax)

def other_is_pos_cmp(
  node: pdftypes.ClassificationNode,
  other: pdftypes.ClassificationNode,
  vert: bool,
  above: bool,
):
  if node.line is not None:
    if other.line is not None:
      return other_is_pos_gte_this(this=node.line, other=other.line, vert=vert, above=above)
    else:
      return other_is_pos_gte_this(this=node.line, other=other.bbox, vert=vert, above=above)
  elif other.line is not None:
    return other_is_pos_gte_this(this=node.bbox, other=other.line, vert=vert, above=above)
  idx0, idx1 = get_idx_for_vert(vert=vert)
  if above:
    return other.bbox[idx0] >= node.bbox[idx1]
  else:
    return other.bbox[idx1] <= node.bbox[idx0]

def get_aligns_in_direction(
  this: typing.Union[pdftypes.Bbox, path_utils.LinePointsType],
  other: typing.Union[pdftypes.Bbox, path_utils.LinePointsType],
  vert: bool
):
  distance_perpendicular = get_distance_between(
    this=this,
    other=other,
    vert=not vert
  )
  return distance_perpendicular == 0

def join_text_line(
  nodes: typing.List[pdftypes.ClassificationNode],
) -> str:
  out = ""
  has_no_text = True
  idx0 = 0
  idx2 = 2
  if len(nodes) > 0 and nodes[0].text is not None:
    out += nodes[0].text
    has_no_text = False
    if isinstance(nodes[0], pdfminer.layout.LTChar) and not nodes[0].left_right:
      idx0 = 1
      idx2 = 3
  for idx in range(1, len(nodes)):
    last_elem = nodes[idx-1]
    elem = nodes[idx]
    elem_width = max(
      elem.bbox[idx2]-elem.bbox[idx0],
      last_elem.bbox[idx2]-last_elem.bbox[idx0]
    )
    x_space = elem.bbox[idx0] - last_elem.bbox[idx2]
    if x_space > 0.5 * elem_width:
      out += ""
    if elem.text is None:
      if len(out) > 0 and out[-1] != "/" and out[-1] != " ":
        if elem.line and elem.slope < 3 and elem.slope > 0.75 and elem.length < 50:
          # TODO: other kinds of shapes
          out += "/"
    else:
      if elem.text == '"' and len(out) > 0 and out[-1] == "/":
        out = out[:-1]
      out += elem.text
      has_no_text = False
  if has_no_text:
    return ""
  return out

def bounding_bbox(
  elems: typing.Union[
    typing.List[LTJson],
    typing.List[pdftypes.ClassificationNode]
  ]
):
  if len(elems) == 0:
    return 0, 0, 1, 1
  x0, y0, x1, y1 = elems[0].bbox
  xmin = x0
  ymin = y0
  xmax = x1
  ymax = y1
  for elem in elems:
    x0, y0, x1, y1 = elem.bbox
    xmin = min(xmin, x0)
    ymin = min(ymin, y0)
    xmax = max(xmax, x1)
    ymax = max(ymax, y1)
  return xmin, ymin, xmax, ymax

def bbox_circumference(bbox: BboxType):
  return 2 * (bbox[2] - bbox[0]) + 2 * (bbox[3] - bbox[1])

def bounding_bbox_nested(nested: typing.List[typing.List[LTJson]]):
  if len(nested) == 0:
    return 0, 0, 1, 1
  biggest = bounding_bbox(elems=nested[0])
  biggest_circum = bbox_circumference(biggest)
  for elems in nested:
    potential = bounding_bbox(elems=elems)
    circum = bbox_circumference(potential)
    if circum > biggest_circum:
      biggest = potential
      biggest_circum = circum
  return biggest
