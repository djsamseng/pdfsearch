
import collections
import math
import typing

from . import path_utils, leafgrid, pdftypes

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
  cycle_start_node: pdftypes.ClassificationNode,
  ordered_dict: typing.OrderedDict[
    pdftypes.ClassificationNode,
    bool
  ],
):
  out: typing.List[pdftypes.ClassificationNode] = []
  for node in ordered_dict.keys():
    if len(out) > 0:
      out.append(node)
    elif node == cycle_start_node:
      out.append(node)
  return out

def find_cyclical_within(
  start_node: pdftypes.ClassificationNode,
  point_to_nodes: typing.DefaultDict[
    path_utils.PointType,
    typing.List[pdftypes.ClassificationNode]
  ],
  nodes_traversed: typing.Set[pdftypes.ClassificationNode],
):
  # Priority queue, DFS, explore all possibilities from a line
  q: typing.List[
    typing.OrderedDict[
      pdftypes.ClassificationNode,
      bool,
    ]
  ] = [collections.OrderedDict()]
  q[0][start_node] = True
  nodes_traversed.add(start_node)
  circles: typing.List[typing.List[pdftypes.ClassificationNode]] = []
  while len(q) > 0:
    nodes_so_far = q.pop()
    cur_node = next(reversed(nodes_so_far))
    cur_line = cur_node.line
    if cur_line is None:
      continue
    use_end = nodes_so_far[cur_node]
    if use_end:
      _, _, x, y = cur_line
    else:
      x, y, _, _ = cur_line
    next_nodes = point_to_nodes[(x, y)]
    for next_node in next_nodes:
      next_line = next_node.line
      if next_line is not None:
        if next_line != cur_line and next_node in nodes_so_far:
          cycle = extract_cycle_from_ordered_dict(
            cycle_start_node=next_node,
            ordered_dict=nodes_so_far,
          )
          if len(cycle) > 5 and check_circle_angles_from_ordered_lines(ordered_lines=[n.line for n in cycle if n.line is not None]):
            circles.append(cycle)
        elif next_node not in nodes_traversed:
          nodes_traversed.add(next_node)
          new_dict: typing.OrderedDict[
            pdftypes.ClassificationNode,
            bool,
          ] = collections.OrderedDict()
          for node_so_far, use_end in nodes_so_far.items():
            new_dict[node_so_far] = use_end
          if (next_line[0], next_line[1]) == (x, y):
            new_dict[next_node] = True
          else:
            new_dict[next_node] = False
          q.append(new_dict)

  return circles

# Split lines at points where another line intersects
#   - Fill a grid with line points at low granularity to get potential intersections
# Create parent nodes for identifying shapes (ex: circle r1, r2) which we can compare
#   - circle, hexagon, trapezoid, square, rectangle, curve (source, dest)
# Table has columns and rows
def identify_from_lines(
  nodes: typing.List[pdftypes.ClassificationNode],
  leaf_grid: leafgrid.LeafGrid,
) -> typing.Tuple[
  typing.List[typing.List[pdftypes.ClassificationNode]],
  typing.Set[path_utils.PointType],
]:
  point_to_nodes: typing.DefaultDict[
    typing.Tuple[float, float],
    typing.List[pdftypes.ClassificationNode]
  ] = collections.defaultdict(list)
  all_intersection_pts: typing.Set[path_utils.PointType] = set()
  pts_hit: typing.Set[path_utils.PointType] = set()
  for node in nodes:
    line = node.line
    if line is not None:
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
      point_to_nodes[(x0, y0)].append(node)
      point_to_nodes[(x1, y1)].append(node)

  nodes_set = set(nodes)
  nodes_traversed: typing.Set[pdftypes.ClassificationNode] = set()
  remaining = nodes_set.difference(nodes_traversed)
  all_circles: typing.List[typing.List[pdftypes.ClassificationNode]] = []
  while len(remaining) > 0:
    start_node = remaining.pop()
    nodes_traversed.add(start_node)
    circles = find_cyclical_within(
      start_node=start_node,
      point_to_nodes=point_to_nodes,
      nodes_traversed=nodes_traversed,
    )
    all_circles.extend(circles)

  return all_circles, all_intersection_pts
