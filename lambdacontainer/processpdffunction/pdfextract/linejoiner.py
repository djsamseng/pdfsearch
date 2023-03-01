
import collections
import math
import typing

from . import path_utils, leafgrid

def check_circle_angles_from_ordered_lines(
  ordered_lines: typing.List[path_utils.LinePointsType],
):
  cur_angle = path_utils.line_angle(line=ordered_lines[0])
  for next_line in ordered_lines:
    next_angle = path_utils.line_angle(line=next_line)
    angle_diff = path_utils.get_angle_diff(a=cur_angle, b=next_angle, directional=False)
    if angle_diff > 20:
      return False

    cur_angle = next_angle
  return True

def extract_cycle_from_ordered_dict(
  cycle_start_line: path_utils.LinePointsType,
  ordered_dict: typing.OrderedDict[
    path_utils.LinePointsType,
    bool
  ],
):
  out: typing.List[path_utils.LinePointsType] = []
  for line in ordered_dict.keys():
    if len(out) > 0:
      out.append(line)
    elif line == cycle_start_line:
      out.append(line)
  return out

def find_cyclical_within(
  start_line: path_utils.LinePointsType,
  point_to_lines: typing.DefaultDict[
    path_utils.PointType,
    typing.List[path_utils.LinePointsType]
  ],
  lines_traversed: typing.Set[path_utils.LinePointsType],
):
  # Priority queue, DFS, explore all possibilities from a line
  q: typing.List[
    typing.OrderedDict[
      path_utils.LinePointsType,
      bool,
    ]
  ] = [collections.OrderedDict()]
  q[0][start_line] = True
  lines_traversed.add(start_line)
  circles: typing.List[typing.List[path_utils.LinePointsType]] = []
  while len(q) > 0:
    lines_so_far = q.pop()
    cur_line = next(reversed(lines_so_far))
    use_end = lines_so_far[cur_line]
    if use_end:
      _, _, x, y = cur_line
    else:
      x, y, _, _ = cur_line
    next_lines = point_to_lines[(x, y)]
    for next_line in next_lines:
      if next_line != cur_line and next_line in lines_so_far:
        cycle = extract_cycle_from_ordered_dict(
          cycle_start_line=next_line,
          ordered_dict=lines_so_far,
        )
        if len(cycle) > 5 and check_circle_angles_from_ordered_lines(ordered_lines=cycle):
          circles.append(cycle)
      elif next_line not in lines_traversed:
        lines_traversed.add(next_line)
        new_dict: typing.OrderedDict[
          path_utils.LinePointsType,
          bool,
        ] = collections.OrderedDict()
        for line_so_far, use_end in lines_so_far.items():
          new_dict[line_so_far] = use_end
        if (next_line[0], next_line[1]) == (x, y):
          new_dict[next_line] = True
        else:
          new_dict[next_line] = False
        q.append(new_dict)

  return circles

# Split lines at points where another line intersects
#   - Fill a grid with line points at low granularity to get potential intersections
# Create parent nodes for identifying shapes (ex: circle r1, r2) which we can compare
#   - circle, hexagon, trapezoid, square, rectangle, curve (source, dest)
# Table has columns and rows
def identify_from_lines(
  lines: typing.List[path_utils.LinePointsType],
  leaf_grid: leafgrid.LeafGrid,
) -> typing.Tuple[
  typing.List[typing.List[path_utils.LinePointsType]],
  typing.Set[path_utils.PointType],
]:
  point_to_lines: typing.DefaultDict[
    typing.Tuple[float, float],
    typing.List[path_utils.LinePointsType]
  ] = collections.defaultdict(list)
  all_intersection_pts: typing.Set[path_utils.PointType] = set()
  pts_hit: typing.Set[path_utils.PointType] = set()
  for line in lines:
    intersection_pts = leaf_grid.line_intersection(line=line)
    for pt in intersection_pts:
      all_intersection_pts.add(pt)
    x0, y0, x1, y1 = line
    if (x0, y0) in pts_hit:
      all_intersection_pts.add((x0, y0))
    if (x1, y1) in pts_hit:
      all_intersection_pts.add((x1, y1))
    pts_hit.add((x0, y0))
    pts_hit.add((x1, y1))
    point_to_lines[(x0, y0)].append(line)
    point_to_lines[(x1, y1)].append(line)

  lines_set = set(lines)
  lines_traversed: typing.Set[path_utils.LinePointsType] = set()
  remaining = lines_set.difference(lines_traversed)
  all_circles: typing.List[typing.List[path_utils.LinePointsType]] = []
  while len(remaining) > 0:
    start_line = remaining.pop()
    lines_traversed.add(start_line)
    circles = find_cyclical_within(
      start_line=start_line,
      point_to_lines=point_to_lines,
      lines_traversed=lines_traversed,
    )
    all_circles.extend(circles)

  return all_circles, all_intersection_pts
