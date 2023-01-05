
import typing

import pdfminer, pdfminer.utils


def compute_bezier_points(
  vertices:typing.Tuple[typing.Tuple[float,float],typing.Tuple[float,float],typing.Tuple[float,float],typing.Tuple[float,float]],
  numPoints:int=30
):
  result: typing.List[typing.Tuple[int,int]] = []

  b0x = vertices[0][0]
  b0y = vertices[0][1]
  b1x = vertices[1][0]
  b1y = vertices[1][1]
  b2x = vertices[2][0]
  b2y = vertices[2][1]
  b3x = vertices[3][0]
  b3y = vertices[3][1]

  # Compute polynomial coefficients from Bezier points
  ax = -b0x + 3 * b1x + -3 * b2x + b3x
  ay = -b0y + 3 * b1y + -3 * b2y + b3y

  bx = 3 * b0x + -6 * b1x + 3 * b2x
  by = 3 * b0y + -6 * b1y + 3 * b2y

  cx = -3 * b0x + 3 * b1x
  cy = -3 * b0y + 3 * b1y

  dx = b0x
  dy = b0y

  # Set up the number of steps and step size
  numSteps = numPoints - 1 # arbitrary choice
  h = 1.0 / numSteps # compute our step size

  # Compute forward differences from Bezier points and "h"
  pointX = dx
  pointY = dy

  firstFDX = ax * (h * h * h) + bx * (h * h) + cx * h
  firstFDY = ay * (h * h * h) + by * (h * h) + cy * h


  secondFDX = 6 * ax * (h * h * h) + 2 * bx * (h * h)
  secondFDY = 6 * ay * (h * h * h) + 2 * by * (h * h)

  thirdFDX = 6 * ax * (h * h * h)
  thirdFDY = 6 * ay * (h * h * h)

  # Compute points at each step
  result.append((int(pointX), int(pointY)))

  for _ in range(numSteps):
      pointX += firstFDX
      pointY += firstFDY

      firstFDX += secondFDX
      firstFDY += secondFDY

      secondFDX += thirdFDX
      secondFDY += thirdFDY

      result.append((int(pointX), int(pointY)))

  return result

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
      pt = typing.cast(typing.Tuple[str, typing.Tuple[float, float], typing.Tuple[float, float], typing.Tuple[float, float]], pt)
      (x2, y2), (x3, y3), (x4, y4) = pt[1:]
      bezier_points = compute_bezier_points(vertices=((x, y), (x2, y2), (x3, y3), (x4, y4)))
      for bezier_idx in range(1, len(bezier_points)):
        bezier_x_start, bezier_y_start = bezier_points[bezier_idx - 1]
        bezier_x_end, bezier_y_end = bezier_points[bezier_idx]
        lines.append(((bezier_x_start, bezier_y_start), (bezier_x_end, bezier_y_end)))
      x, y = x4, y4
    elif pt_type == "h":
      lines.append(((x, y), (x_start, y_start)))
    else:
      print("Unhandled path point:", pt)
  return lines