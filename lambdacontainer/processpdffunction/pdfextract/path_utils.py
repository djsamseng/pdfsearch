
import typing

import pdfminer, pdfminer.utils

BezierPoints = typing.Tuple[
  typing.Tuple[float,float],
  typing.Tuple[float,float],
  typing.Tuple[float,float],
  typing.Tuple[float,float]
]

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
  for t_idx in range(1, 10):
    t = t_idx / 10
    x, y = get_bezier_point(t=t, pts=pts)
    lines.append(((x_prev, y_prev), (x, y)))
    x_prev, y_prev = x, y
  return lines

LinePointsType = typing.Tuple[typing.Tuple[float, float], typing.Tuple[float, float]]

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
      lines.append(((x, y), (x2, y2)))
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
      bezier_lines = bezier_to_lines(pts=((x, y), (x2, y2), (x3, y3), (x4, y4)))
      lines.extend(bezier_lines)
      x, y = bezier_lines[-1][-1]
    elif pt_type == "h":
      lines.append(((x, y), (x_start, y_start)))
    else:
      print("Unhandled path point:", pt)
  return lines

def get_zeroed_path_lines(path_lines: typing.List[LinePointsType]):
  out: typing.List[LinePointsType] = []
  (x0, y0), (x1, y1) = path_lines[0]
  xmin = min(x0, x1)
  ymin = min(y0, y1)
  for (x0, y0), (x1, y1) in path_lines:
    xmin = min(xmin, min(x0, x1))
    ymin = min(ymin, min(y0, y1))
  for (x0, y0), (x1, y1) in path_lines:
    out.append(((x0-xmin, y0-ymin), (x1-xmin, y1-ymin)))
  return out
