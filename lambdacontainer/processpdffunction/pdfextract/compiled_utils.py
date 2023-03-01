

import typing

import numba.types
from numba.pycc import CC

cc = CC("compiled_utils")
cc.verbose = True


FloatTupleType = numba.types.Tuple([numba.types.float64, numba.types.float64])
LinePointsTypePy = typing.Tuple[float, float, float, float]
LinePointsTypeNumba = numba.types.Tuple([numba.types.float64, numba.types.float64, numba.types.float64, numba.types.float64])

@numba.njit()
@cc.export("points_inside_line_bbox", numba.types.boolean(LinePointsTypeNumba, numba.types.float64, numba.types.float64))
def point_inside_line_bbox(
  line: LinePointsTypePy,
  x: float,
  y: float,
):
  x0, y0, x1, y1 = line
  xmin = min(x0, x1) - 0.1
  ymin = min(y0, y1) - 0.1
  xmax = max(x0, x1) + 0.1
  ymax = max(y0, y1) + 0.1
  x_inside = xmin <= x and x <= xmax
  y_inside = ymin <= y and y <= ymax
  return x_inside and y_inside

@numba.njit()
@cc.export("get_det", numba.types.float64(FloatTupleType, FloatTupleType))
def get_det(
  a: typing.Tuple[float, float],
  b: typing.Tuple[float, float],
):
  return a[0] * b[1] - a[1] * b[0]

@cc.export("line_intersection", FloatTupleType(LinePointsTypeNumba, LinePointsTypeNumba))
def line_intersection(line1: LinePointsTypePy, line2: LinePointsTypePy):
  dx = (line1[0] - line1[2], line2[0] - line2[2])
  dy = (line1[1] - line1[3], line2[1] - line2[3])

  div = get_det(a=dx, b=dy)
  if div == 0:
    return (-1, -1)

  d = (get_det(a=line1[0:2], b=line1[2:4]), get_det(a=line2[0:2], b=line2[2:4]))
  x = get_det(a=d, b=dx) / div
  y = get_det(a=d, b=dy) / div

  if point_inside_line_bbox(line1, x, y):
    if point_inside_line_bbox(line2, x, y):
      return x, y

  return (-1, -1)

# cc.compile()
