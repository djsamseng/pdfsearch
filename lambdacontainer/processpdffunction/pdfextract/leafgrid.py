
import collections
import heapq
import functools
import math
import typing

from . import pdftypes, pdfelemtransforms, path_utils

def coord_for_step_size(x: float, step_size: int) -> int:
  return math.floor(x / step_size)

class GridNode(object):
  def __init__(self, node_id: int, node: pdftypes.ClassificationNode) -> None:
    self.node_id = node_id
    self.node = node

  def __repr__(self) -> str:
    return "{0} {1}".format(self.node_id, self.node)

GridType = typing.List[typing.List[typing.List[GridNode]]]

def coords_for_line(
  line: path_utils.LinePointsType,
  coord_for: typing.Callable[[float], int]
):
  x0, y0, x1, y1 = line
  slope = path_utils.line_slope(line=line)
  if abs(x1 - x0) > abs(y1 - y0):
    x0, y0, x1, y1 = coord_for(x0), coord_for(y0), coord_for(x1), coord_for(y1)
    for x in range(x0, x1+1):
      y = math.floor((x - x0) * slope + y0)
      yield x, y
  else:
    x0, y0, x1, y1 = coord_for(x0), coord_for(y0), coord_for(x1), coord_for(y1)
    ymin = min(y0, y1)
    ymax = max(y0, y1)
    for y in range(ymin, ymax+1):
      if slope == path_utils.MAX_SLOPE:
        x = x0
      else:
        x = math.floor((y - y0) / slope + x0)
      yield x, y

class LeafGrid():
  def __init__(
    self,
    celems: typing.List[pdftypes.ClassificationNode],
    width: int,
    height: int,
    step_size: int
  ) -> None:
    coord_for = functools.partial(coord_for_step_size, step_size=step_size)
    self.coord_for = coord_for
    self.celems = celems
    self.grid: GridType = [
      [
        [] for _ in range(coord_for(width)+1)]
      for _ in range(coord_for(height)+1)
    ]
    def insert_elems(grid: GridType, celems: typing.List[pdftypes.ClassificationNode]):
      for node in celems:
        if node.text is not None:
          x0, y0, x1, y1 = node.bbox
          x0, y0, x1, y1 = coord_for(x0), coord_for(y0), coord_for(x1), coord_for(y1)
          for y in range(y0, y1+1):
            for x in range(x0, x1+1):
              grid[y][x].append(GridNode(node_id=node.node_id, node=node))
        elif node.line is not None:
          for x, y in coords_for_line(line=node.line, coord_for=coord_for):
            grid[y][x].append(GridNode(node_id=node.node_id, node=node))

    def sort_grid(grid: GridType):
      for y in range(len(grid)):
        for x in range(len(grid[y])):
          grid[y][x].sort(key=functools.cmp_to_key(self.sort_func_xy))

    insert_elems(grid=self.grid, celems=celems)
    sort_grid(grid=self.grid)

  def insert_elem(self, node: pdftypes.ClassificationNode):
    node_id = len(self.celems)
    self.celems.append(node)
    x0, y0, x1, y1 = node.bbox
    x0, y0, x1, y1 = self.coord_for(x0), self.coord_for(y0), self.coord_for(x1), self.coord_for(y1)
    for y in range(y0, y1+1):
      for x in range(x0, x1+1):
        heapq.heappush(self.grid[y][x], GridNode(node_id=node_id, node=node))

  def first_elem(self, bbox: pdftypes.Bbox, text_only:bool):
    x0 = self.coord_for(math.floor(bbox[0]))
    y0 = self.coord_for(math.floor(bbox[1]))
    x1 = self.coord_for(math.ceil(bbox[2]))
    y1 = self.coord_for(math.ceil(bbox[3]))
    for y in range(y1, y0, -1):
      for x in range(x0, x1):
        for elem in self.grid[y][x]:
          if not text_only:
            return elem
          elif elem.node.text is not None:
            return elem
    return None

  def next_elem_for_coords(
    self,
    x0: float, y0: float, x1: float, y1: float,
    direction: pdftypes.Direction,
    restrict_idxes: typing.Dict[int, bool],
  ):
    bbox = (x0, y0, x1, y1)
    x0 = self.coord_for(x0)
    y0 = self.coord_for(y0)
    x1 = self.coord_for(x1)
    y1 = self.coord_for(y1)
    for res in self.process_coords(
      bbox=bbox,
      x0=x0, y0=y0, x1=x1, y1=y1,
      direction=direction,
      restrict_idxes=restrict_idxes,
    ):
      yield res

    def step(x0: int, y0: int, x1: int, y1: int):
      if direction == pdftypes.Direction.LEFT:
        x1 -= 1
      elif direction == pdftypes.Direction.RIGHT:
        x0 += 1
      elif direction == pdftypes.Direction.UP:
        y0 += 1
      elif direction == pdftypes.Direction.DOWN:
        y1 -= 1
      return x0, y0, x1, y1

    x0, y0, x1, y1 = step(x0=x0, y0=y0, x1=x1, y1=y1)

    should_continue = y0 >= 0 and y0 < len(self.grid) and\
       y1 >= 0 and y1 < len(self.grid) and\
       x0 >=0 and x0 < len(self.grid[y1]) and\
       x1 >= 0 and x1 < len(self.grid[y1])
    while should_continue:
      for res in self.process_coords(
        bbox=bbox,
        x0=x0, y0=y0, x1=x1, y1=y1,
        direction=direction,
        restrict_idxes=restrict_idxes,
      ):
        yield res
      x0, y0, x1, y1 = step(x0=x0, y0=y0, x1=x1, y1=y1)
      should_continue = y0 >= 0 and y0 < len(self.grid) and\
       y1 >= 0 and y1 < len(self.grid) and\
       x0 >=0 and x0 < len(self.grid[y1]) and\
       x1 >= 0 and x1 < len(self.grid[y1])
    return None

  def intersection(
    self,
    x0: typing.Union[None, float] = None,
    y0: typing.Union[None, float] = None,
    x1: typing.Union[None, float] = None,
    y1: typing.Union[None, float] = None,
    query: typing.Union[None, pdftypes.Bbox] = None,
  ) -> typing.List[pdftypes.ClassificationNode]:
    # Return sorted such that
    # If intersects then sorted by x0 left right, y1 top down
    if x0 is None or y0 is None or x1 is None or y1 is None:
      if query is None:
        return []
      x0, y0, x1, y1 = query
    out: typing.List[GridNode] = []
    already_in_out: typing.Dict[int, bool] = {}
    for x in range(self.coord_for(x0), self.coord_for(x1)+1):
      in_this_x: typing.List[GridNode] = []
      for y in range(self.coord_for(y0), self.coord_for(y1)+1):
        for grid_node in self.grid[y][x]:
          if grid_node.node_id in already_in_out:
            continue
          celem = grid_node.node
          if pdfelemtransforms.bbox_intersection_area(a=celem.bbox, b=(x0,y0,x1,y1)) > 0:
            already_in_out[grid_node.node_id] = True
            in_this_x.append(grid_node)
      in_this_x.sort(key=functools.cmp_to_key(self.sort_func_xy))
      out.extend(in_this_x)

    return [ grid_node.node for grid_node in out]

  def line_intersection(
    self,
    line: path_utils.LinePointsType
  ):
    out: typing.DefaultDict[
      path_utils.PointType,
      typing.Set[pdftypes.ClassificationNode]
    ] = collections.defaultdict(set)
    for x, y in coords_for_line(line=line, coord_for=self.coord_for):
      for match in self.grid[y][x]:
        if match.node.line is not None:
          if match.node.line != line:
            line_intersection_pt = path_utils.line_intersection(line1=line, line2=match.node.line)
            if line_intersection_pt[0] >= 0 and line_intersection_pt not in out:
              out[line_intersection_pt].add(match.node)

    return out

  def process_coords(
    self,
    bbox: pdftypes.Bbox,
    x0: int, y0: int, x1: int, y1: int,
    direction: pdftypes.Direction,
    restrict_idxes: typing.Dict[int, bool],
  ):

    def node_can_be_next(node: GridNode):
      if node.node_id in restrict_idxes:
        return False

      vert = direction == pdftypes.Direction.UP or direction == pdftypes.Direction.DOWN
      if pdfelemtransforms.get_aligns_in_direction(
        this=bbox,
        other=node.node.bbox,
        vert=vert
      ):
        return True
      return False


    in_this_box: typing.List[GridNode] = []
    if direction == pdftypes.Direction.LEFT:
      for y in range(y1, y0-1, -1):
        in_this_box.extend([
          b for b in self.grid[y][x1] if
            b.node.bbox[2] <= x1 and # left of me
            node_can_be_next(node=b)
        ])
      sort_func = functools.partial(self.sort_func_custom, order=(2, 3, 1, 0))
    elif direction == pdftypes.Direction.RIGHT:
      for y in range(y1, y0-1, -1):
        in_this_box.extend([
          b for b in self.grid[y][x0] if
            b.node.bbox[0] >= x1 and # right of me
            node_can_be_next(node=b)
        ])
      sort_func = functools.partial(self.sort_func_custom, order=(0, 3, 1, 2))
    elif direction == pdftypes.Direction.UP:
      for x in range(x0, x1):
        in_this_box.extend([
          b for b in self.grid[y0][x] if
            b.node.bbox[1] >= y0 and # above me
            node_can_be_next(node=b)
        ])
      sort_func = functools.partial(self.sort_func_custom, order=(1, 0, 2, 3))
    elif direction == pdftypes.Direction.DOWN:
      for x in range(x0, x1):
        in_this_box.extend([
          b for b in self.grid[y1][x] if
            b.node.bbox[3] <= y0 and # below me
            node_can_be_next(node=b)
        ])
      sort_func = functools.partial(self.sort_func_custom, order=(3, 0, 2, 1))
    in_this_box.sort(key=functools.cmp_to_key(sort_func), reverse=False)
    # print("Process coords:", (x0, y0, x1, y1), len(in_this_box))
    if len(in_this_box) > 0:
      yield in_this_box[0]

  def sort_func_custom(self, a: GridNode, b: GridNode, order: typing.Tuple[int, int, int, int]):
    return sort_func_node(a=a.node, b=b.node, order=order)


  def sort_func_xy(self, a: GridNode, b: GridNode):
    # return -1 if a_idx comes before b_idx
    # Left right by x0, top down by y1, left right by x1, top down by y0
    #                               |---|
    #  |-----|    |---|       |---| | 4 |
    #  |query|    | 1 | |---| | 3 | |---|
    #  |-----|    |---| |-2-| |---|
    #
    return self.sort_func_custom(a=a, b=b, order=(0, 3, 2, 1))

def sort_func_node(
  a: pdftypes.ClassificationNode,
  b: pdftypes.ClassificationNode,
  order: typing.Tuple[int, int, int, int]
):
  if a.bbox[order[0]] < b.bbox[order[0]]:
    return -1
  elif a.bbox[order[0]] == b.bbox[order[0]]:
    if a.bbox[order[1]] > b.bbox[order[1]]:
      return -1
    elif a.bbox[order[1]] == b.bbox[order[1]]:
      if a.bbox[order[2]] < b.bbox[order[2]]:
        return -1
      elif a.bbox[order[2]] == b.bbox[order[2]]:
        if a.bbox[order[3]] > b.bbox[order[3]]:
          return -1
        elif a.bbox[order[3]] == b.bbox[order[3]]:
          return 0
        else:
          return 1
      else:
        return 1
    else:
      return 1
  else:
    return 1
