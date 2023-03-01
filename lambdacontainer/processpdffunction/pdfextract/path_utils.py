
import math
import typing

import pdfminer, pdfminer.utils

from . import compiled_utils

BezierPoints = typing.Tuple[
  typing.Tuple[float,float],
  typing.Tuple[float,float],
  typing.Tuple[float,float],
  typing.Tuple[float,float]
]

LinePointsType = typing.Tuple[float, float, float, float]
OffsetType = typing.Tuple[float, float]
PointType = typing.Tuple[float, float]

Bbox = typing.Tuple[float, float, float, float]
MAX_SLOPE = 1000.

def get_bezier_point(t: float, pts: BezierPoints):
  mults = [
    (1 - t) ** 3,
    3 * t * ((1 - t) ** 2),
    3 * (t ** 2) * (1 - t),
    t ** 3,
  ]
  x = 0.
  y = 0.
  for idx in range(len(mults)):
    x += pts[idx][0] * mults[idx]
    y += pts[idx][1] * mults[idx]
  return (x, y)

def bezier_to_lines(pts: BezierPoints):
  lines: typing.List[LinePointsType] = []
  x_prev, y_prev = get_bezier_point(t=0, pts=pts)
  for t_idx in range(1, 11):
    t = t_idx / 10
    x, y = get_bezier_point(t=t, pts=pts)
    swap_direction = x < x_prev and False
    if swap_direction:
      lines.append((x, y, x_prev, y_prev))
    else:
      lines.append((x_prev, y_prev, x, y))
    x_prev, y_prev = x, y
  return lines, x_prev, y_prev

def path_to_lines(path: typing.List[pdfminer.utils.PathSegment]):
  lines: typing.List[LinePointsType] = []
  x, y = 0, 0
  x_start, y_start = x, y
  for pt in path:
    pt_type = pt[0]
    if pt_type == "m":
      pt = typing.cast(typing.Tuple[str, typing.Tuple[float, float]], pt)
      x, y = pt[1]
      x_start, y_start = x, y
    elif pt_type == "l":
      pt = typing.cast(typing.Tuple[str, typing.Tuple[float, float]], pt)
      x2, y2 = pt[1]
      swap_direction = x2 < x
      if swap_direction:
        lines.append((x2, y2, x, y))
      else:
        lines.append((x, y, x2, y2))
      x, y = x2, y2
    elif pt_type == "c":
      pt = typing.cast(
        typing.Tuple[
          str,
          typing.Tuple[float, float],
          typing.Tuple[float, float],
          typing.Tuple[float, float]
        ],
        pt
      )
      (x2, y2), (x3, y3), (x4, y4) = pt[1:]
      bezier_lines, x_end, y_end = bezier_to_lines(pts=((x, y), (x2, y2), (x3, y3), (x4, y4)))
      lines.extend(bezier_lines)
      x, y = x_end, y_end
    elif pt_type == "h":
      swap_direction = x_start < x
      if swap_direction:
        lines.append((x_start, y_start, x, y))
      else:
        lines.append((x, y, x_start, y_start))
    else:
      print("Unhandled path point:", pt)
  return lines

def get_zeroed_path_lines(path_lines: typing.List[LinePointsType]):
  out: typing.List[LinePointsType] = []
  x0, y0, x1, y1 = path_lines[0]
  xmin = min(x0, x1)
  ymin = min(y0, y1)
  for x0, y0, x1, y1 in path_lines:
    xmin = min(xmin, x0, x1)
    ymin = min(ymin, y0, y1)
  for x0, y0, x1, y1 in path_lines:
    out.append((x0-xmin, y0-ymin, x1-xmin, y1-ymin))
  return out

def lines_bounding_bbox(
  elems: typing.List[LinePointsType],
  offsets: typing.Union[None, typing.List[OffsetType]] = None,
):
  if len(elems) == 0:
    return 0, 0, 1, 1
  def offset_for(idx: int):
    if offsets is None:
      return 0., 0.,
    return offsets[idx][0], offsets[idx][1]
  x0, y0, x1, y1 = elems[0]
  ox, oy = offset_for(idx=0)
  xmin = min(x0, x1) + ox
  ymin = min(y0, y1) + oy
  xmax = max(x0, x1) + ox
  ymax = max(y0, y1) + oy
  for idx, elem in enumerate(elems):
    x0, y0, x1, y1 = elem
    ox, oy = offset_for(idx=idx)
    xmin = min(xmin, x0, x1) + ox
    ymin = min(ymin, y0, y1) + oy
    xmax = max(xmax, x0, x1) + ox
    ymax = max(ymax, y0, y1) + oy
  return xmin, ymin, xmax, ymax

def zero_line(line: LinePointsType, bounding_box: Bbox) -> LinePointsType:
  return (
    line[0] - bounding_box[0],
    line[1] - bounding_box[1],
    line[2] - bounding_box[0],
    line[3] - bounding_box[1],
  )

def sign(val: float) -> int:
  if val == 0:
    return 0
  elif val < 0:
    return -1
  return 1

def line_slope(line: LinePointsType):
  x0, y0, x1, y1 = line
  rise = y1 - y0
  run = x1 - x0
  if abs(run) < 1 / MAX_SLOPE:
    slope = MAX_SLOPE * (1 if run >= 0 else -1)
  else:
    slope = rise / run
  if slope > 0:
    slope = min(slope, MAX_SLOPE)
  else:
    slope = max(slope, -MAX_SLOPE)
  return slope

def get_angle(dx: float, dy: float):
  # Top = 0
  # Left = -90
  # Right = 90
  # bottom = -179, 180, 179
  angle = math.degrees(math.atan2(dy, dx))
  return angle

def line_angle(line: LinePointsType):
  x0, y0, x1, y1 = line
  return get_angle(
    dx=x1 - x0,
    dy=y1 - y0
  )

def get_angle_diff_impl(
  a: float,
  b: float,
):
  # 1 - -1 = 2 => 2
  # 180 - -1 = 180 + 1 => 180-1
  # 180 - -180 = 360 => 0
  # 172 - 7.95
  # >>> get_angle_diff(180*0.7, 180)
  # 54.000000000000014
  # >>> get_angle_diff(180*0.7, -180)
  # 54.0
  # >>> get_angle_diff(-180*0.7, -180)
  # 54.000000000000014
  # >>> get_angle_diff(180*0.7, 180)
  # 54.000000000000014
  # >>> get_angle_diff(180*0.7, 180*0.7)
  # 0.0
  # >>> get_angle_diff(180*0.7, -180*0.7)
  # 108.00000000000003 = 180 * 0.3 * 2
  diff = abs(a - b)
  if diff > 180:
    return 360 - abs(diff)
  return diff

def get_angle_diff(
  a: float,
  b: float,
  directional: bool=True,
):
  if not directional:
    if a < 0:
      flipped_a = 180 + a
    else:
      flipped_a = -(180 - a)
    return min(
      get_angle_diff_impl(a=a, b=b),
      get_angle_diff_impl(a=flipped_a, b=b),
    )
  return get_angle_diff_impl(a=a, b=b)

def line_length(line: LinePointsType):
  x0, y0, x1, y1 = line
  return math.sqrt((y1-y0) ** 2 + (x1-x0) ** 2)

def line_offset(a: LinePointsType, b: LinePointsType) -> OffsetType:
  return (
    a[0] - b[0],
    a[1] - b[1]
  )

def point_inside_line_bbox(
  line: LinePointsType,
  x: float,
  y: float,
):
  return compiled_utils.point_inside_line_bbox(line, x, y)

def line_intersection(
  line1: LinePointsType,
  line2: LinePointsType
) -> typing.Tuple[float, float]:
  return compiled_utils.line_intersection(line1, line2)

def line_pairwise_offsets(lines: typing.List[LinePointsType]):
  out: typing.List[typing.List[OffsetType]] = []
  for line1 in lines:
    line1_offsets: typing.List[OffsetType] = []
    for line2 in lines:
      line1_offsets.append(
        line_offset(a=line1, b=line2)
      )
    out.append(line1_offsets)
  return out
