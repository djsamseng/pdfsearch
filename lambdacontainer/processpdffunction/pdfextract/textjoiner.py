
import typing

import pdfminer, pdfminer.layout
import rtree, rtree.index


from . import pdftypes, path_utils, pdfelemtransforms, nodemanager

class TextJoiner():
  def __init__(
    self,
    layer_nodes: typing.List[pdftypes.ClassificationNode],
    layer_rtree: rtree.index.Index,
  ) -> None:
    self.layer_nodes = layer_nodes
    self.layer_rtree = layer_rtree
    self.join_rtree = rtree.index.Index()

    self.nodes: typing.List[pdftypes.ClassificationNode] = []

  def join(
    self,
  ):
    def get_query_for_node(node: pdftypes.ClassificationNode):
      x0, y0, x1, y1 = node.bbox
      divisor = len(node.text) if node.text is not None else 1
      divisor = max(divisor, 1)
      if isinstance(node.elem, pdfminer.layout.LTChar) and not node.elem.upright:
        y0 -= node.elem.height / divisor
        y1 += node.elem.height / divisor
      else:
        x0 -= node.width() / divisor
        x1 += node.width() / divisor
      query = (
        x0,
        y0,
        x1,
        y1,
      )
      return query
    pending_nodes: typing.List[pdftypes.ClassificationNode] = []
    node_ids_stranded: typing.Set[int] = set()
    for node in self.layer_nodes:
      if node.text is not None:
        query = get_query_for_node(node=node)
        joined_node = self.__add(query_coords=query, node=node, node_ids_stranded=node_ids_stranded)
        if joined_node is not None:
          pending_nodes.append(joined_node)

    while len(pending_nodes) > 0:
      node = pending_nodes.pop()
      query = get_query_for_node(node=node)
      joined_node = self.__add(query_coords=query, node=node, node_ids_stranded=node_ids_stranded)
      if joined_node is not None:
        pending_nodes.append(joined_node)
    return [self.nodes[idx] for idx in node_ids_stranded]

  def __add(
    self,
    query_coords: path_utils.Bbox,
    node: pdftypes.ClassificationNode,
    node_ids_stranded: typing.Set[int],
  ) -> typing.Union[None, pdftypes.ClassificationNode]:
    idxes = self.join_rtree.intersection(coordinates=query_coords, objects=False)
    idxes = list(idxes)
    if len(idxes) > 0:
      connecting = [ self.nodes[idx] for idx in idxes ]
      connecting.append(node)
      # TODO: Figure out where to insert lines after full join instead of during to prevent double adds
      lines_idxes = self.layer_rtree.intersection(coordinates=query_coords, objects=False)
      lines_idxes = list(lines_idxes)
      left_right = node.left_right
      if not left_right:
        connecting.sort(key=lambda n: n.bbox[1])
      else:
        connecting.sort(key=lambda n: n.bbox[0])

      joined_text = pdfelemtransforms.join_text_line(nodes=connecting)
      joined_bbox = pdfelemtransforms.bounding_bbox(elems=[c for c in connecting if c.text is not None])
      delete_idxes = idxes
      for idx in delete_idxes:
        self.join_rtree.delete(id=idx, coordinates=self.nodes[idx].bbox)
        if idx in node_ids_stranded:
          node_ids_stranded.remove(idx)
      # TODO: Allow overlapping words
      joined_node = pdftypes.ClassificationNode(
        elem=None,
        bbox=joined_bbox,
        line=None,
        text=joined_text,
        child_ids=delete_idxes,
      )
      joined_node.left_right = left_right
      return joined_node
    else:
      idx = len(self.nodes)
      self.join_rtree.add(idx, coordinates=node.bbox, obj=None)
      self.nodes.append(node)
      node_ids_stranded.add(idx)
      return None


def get_node_neighbors(
  node: pdftypes.ClassificationNode,
  neighbors: typing.List[pdftypes.ClassificationNode]
):
  # TODO: overlap
  closest_above: typing.Union[pdftypes.ClassificationNode, None] = None
  closest_above_space = 1000
  closest_right: typing.Union[pdftypes.ClassificationNode, None] = None
  closest_right_space = 1000
  closest_below: typing.Union[pdftypes.ClassificationNode, None] = None
  closest_below_space = 1000
  closest_left: typing.Union[pdftypes.ClassificationNode, None] = None
  closest_left_space = 1000
  for other in neighbors:
    if other.node_id == node.node_id:
      continue
    is_above = pdfelemtransforms.other_is_pos_cmp(node=node, other=other, vert=True, above=True)
    is_right = pdfelemtransforms.other_is_pos_cmp(node=node, other=other, vert=False, above=True)
    is_below = pdfelemtransforms.other_is_pos_cmp(node=node, other=other, vert=True, above=False)
    is_left = pdfelemtransforms.other_is_pos_cmp(node=node, other=other, vert=False, above=False)
    distance_x = pdfelemtransforms.get_distance_between(this=node.bbox, other=other.bbox, vert=False)
    distance_y = pdfelemtransforms.get_distance_between(this=node.bbox, other=other.bbox, vert=True)
    if is_above and distance_x == 0:
      if closest_above is None or distance_y < closest_above_space:
        closest_above = other
        closest_above_space = distance_y
    if is_right and distance_y == 0:
      if closest_right is None or distance_x < closest_right_space:
        closest_right = other
        closest_right_space = distance_x
    if is_below and distance_x == 0:
      if closest_below is None or distance_y < closest_below_space:
        closest_below = other
        closest_below_space = distance_y
    if is_left and distance_y == 0:
      if closest_left is None or distance_x < closest_left_space:
        closest_left = other
        closest_left_space = distance_x
  return closest_left, closest_below, closest_right, closest_above

def make_query(node: pdftypes.ClassificationNode):
  x0, y0, x1, y1 = node.bbox
  if node.left_right:
    return (
      x0 - node.width(),
      y0,
      x1 + node.width(),
      y1,
    )
  else:
    return (
      x0,
      y0 - node.height(),
      x1,
      y1 + node.height()
    )

def make_query_square(node: pdftypes.ClassificationNode, radius: float):
  x0, y0, x1, y1 = node.bbox
  return (
    x0 - radius,
    y0 - radius,
    x1 + radius,
    y1 + radius,
  )

def get_boundaries_str(
  boundaries: pdftypes.Boundaries,
):
  out = "("
  for idx in range(len(boundaries)):
    bound = boundaries[idx]
    if bound is None:
      out += "-1,"
    else:
      out += "{0:.2f},".format(bound[0])
  return out[:-1] + ")"

def set_boundaries(
  start: pdftypes.ClassificationNode,
  node: pdftypes.ClassificationNode,
  boundaries: pdftypes.Boundaries,
):
  if node.line is not None:
    x0, y0, x1, y1 = node.line
    if abs(node.slope) < 0.5 and node.width() >= start.width():
      # Horizontal line
      width_overlap = pdfelemtransforms.get_overlap_in_direction(
        this=start.bbox,
        other=node.bbox,
        height_overlap=False,
      )
      if width_overlap >= start.width():
        if y0 < start.bbox[1]:
          if boundaries[1] is None:
            boundaries[1] = (node.bbox[1], node)
          elif y0 > boundaries[1][0]:
            boundaries[1] = (node.bbox[1], node)
        if y1 > start.bbox[3]:
          if boundaries[3] is None:
            boundaries[3] = (node.bbox[3], node)
          elif y1 < boundaries[3][0]:
            boundaries[3] = (node.bbox[3], node)
    elif abs(node.slope) > 5 and node.height() >= start.height():
      # Vertical line
      height_overlap = pdfelemtransforms.get_overlap_in_direction(
        this=start.bbox,
        other=node.bbox,
        height_overlap=True
      )
      if height_overlap >= start.height():
        if x0 < start.bbox[0]:
          if boundaries[0] is None:
            boundaries[0] = (node.bbox[0], node)
          elif x0 > boundaries[0][0]:
            boundaries[0] = (node.bbox[0], node)
        if x1 > start.bbox[2]:
          if boundaries[2] is None:
            boundaries[2] = (node.bbox[2], node)
          elif x1 < boundaries[2][0]:
            boundaries[2] = (node.bbox[2], node)

FONT_SIZE_DIFF = 1
def node_should_add_to_group_split_space(
  processing: pdftypes.ClassificationNode,
  node: pdftypes.ClassificationNode,
  group: typing.Set[pdftypes.ClassificationNode],
):
  return node_should_add_to_group_impl(
    processing=processing,
    node=node,
    group=group,
    allow_space=False,
  )

def node_should_add_to_group_join_space(
  processing: pdftypes.ClassificationNode,
  node: pdftypes.ClassificationNode,
  group: typing.Set[pdftypes.ClassificationNode],
):
  return node_should_add_to_group_impl(
    processing=processing,
    node=node,
    group=group,
    allow_space=True,
  )

def node_should_add_to_group_impl(
  processing: pdftypes.ClassificationNode,
  node: pdftypes.ClassificationNode,
  group: typing.Set[pdftypes.ClassificationNode],
  allow_space: bool,
):
  if node in group:
    return False
  node.labelize()
  radius = 1
  if node.text is not None:
    if node.left_right != processing.left_right:
      return False
    if abs(node.fontsize - processing.fontsize) > FONT_SIZE_DIFF:
      return False
    if not allow_space and node.text == " ":
      return False
    idx0, idx1 = pdfelemtransforms.get_idx_for_vert(vert=not processing.left_right)
    perpendicular_overlap = pdfelemtransforms.get_overlap_in_direction(
      this=processing.bbox,
      other=node.bbox,
      height_overlap=processing.left_right,
    )
    start_perpendicular_size = processing.height() if processing.left_right else processing.width()
    if abs(perpendicular_overlap - start_perpendicular_size) > FONT_SIZE_DIFF:
      if processing.labels[pdftypes.LabelType.FRACTION] > 0:
        if perpendicular_overlap / start_perpendicular_size > 0.25:
          # Enough overlap
          if processing.bbox[idx0] < node.bbox[idx0] and processing.bbox[idx1] > node.bbox[idx1]:
            # Centered
            return True
          if processing.bbox[idx0] > node.bbox[idx0] and processing.bbox[idx1] < node.bbox[idx1]:
            # Centered
            return True
      return False

    node_is_touching_left = abs(node.bbox[idx1] - processing.bbox[idx0]) < radius
    node_is_touching_right = abs(node.bbox[idx0] - processing.bbox[idx1]) < radius
    if node_is_touching_left or node_is_touching_right:
      return True
  return False

def cluster_text_group(
  node_manager: nodemanager.NodeManager,
  start: pdftypes.ClassificationNode,
  source_layer_idx: int,
  node_should_add_to_group_func: typing.Callable[
    [pdftypes.ClassificationNode, pdftypes.ClassificationNode, typing.Set[pdftypes.ClassificationNode]],
  bool],
):
  # Get my neighbors, find what I'm connected to
  # If I'm text then I don't connect to a much larger line
  # Joined text can connect to a large line if they are above the same size
  # Keep connecting until no nodes in my group can connect
  query = make_query(node=start)
  neighbors = node_manager.intersection(layer_idx=source_layer_idx, bbox=query) #leaf_grid.intersection(query=query)

  group: typing.Set[pdftypes.ClassificationNode] = set()
  group.add(start)
  to_process: typing.List[pdftypes.ClassificationNode] = [start]

  while len(to_process) > 0:
    added_node = to_process.pop()
    query = make_query(node=added_node)
    neighbors = node_manager.intersection(layer_idx=source_layer_idx, bbox=query) #leaf_grid.intersection(query=query)
    neighbors.sort(key=lambda n: pdfelemtransforms.get_node_distance_to(other=n, src=added_node))
    for node in neighbors:
      if node_should_add_to_group_func(added_node, node, group):
        group.add(node)
        to_process.append(node)

  out = list(group)
  if start.left_right:
    out.sort(key=lambda n: n.bbox[0])
  else:
    out.sort(key=lambda n: n.bbox[3])
  out_text = pdfelemtransforms.join_text_line(nodes=out)
  bounding_bbox = pdfelemtransforms.bounding_bbox(elems=out)
  child_ids = [n.node_id for n in out]
  group_parent = node_manager.add_node(
    elem=None,
    bbox=bounding_bbox,
    line=None,
    text=out_text,
    left_right=start.left_right,
    child_ids=child_ids,
    layer_id=source_layer_idx+1,
  )
  group_parent.labelize()
  return group_parent

def cluster_text_by_connected_groups(
  node_manager: nodemanager.NodeManager,
  source_layer_idx: int,
  node_should_add_to_group_func: typing.Callable[
    [pdftypes.ClassificationNode, pdftypes.ClassificationNode, typing.Set[pdftypes.ClassificationNode]],
  bool],
):
  nodes_used: typing.Set[
    pdftypes.ClassificationNode,
  ] = set()
  layer_nodes = [node_manager.nodes[node_id] for node_id in node_manager.layers[source_layer_idx]]
  text_nodes = set([n for n in layer_nodes if n.text is not None])
  remaining = text_nodes.difference(nodes_used)
  groups: typing.List[pdftypes.ClassificationNode] = []
  # remaining = [ node_manager.nodes[17275]] # H in HARDWARE
  # remaining = [node_manager.nodes[3282]]
  # remaining = [ node_manager.nodes[17229]] # schedule 3 in 3/4
  # remaining = [ node_manager.nodes[17227]] # schedule 1 in 1 3/4
  # remaining = [ node_manager.nodes[19926], node_manager.nodes[19949]]
  # TODO: Fix: remaining = [ node_manager.nodes[19926], node_manager.nodes[19949]]
  # TODO: Fix: remaining = [ node_manager.nodes[21200]]
  # TODO: Join [2348, 2390, 3447, 3448, 3454, 3455, 3456, 3457, 3458, 3466, 3467, 3468, 3469, 3470, 3471]
  #    - Use known words
  is_dev = len(remaining) <= 2
  while len(remaining) > 0:
    start_node = remaining.pop()

    if is_dev:
      print("Start:", start_node.bbox, start_node.text)
    parent = cluster_text_group(
      node_manager=node_manager,
      start=start_node,
      source_layer_idx=0,
      node_should_add_to_group_func=node_should_add_to_group_func,
    )
    for child_id in parent.child_ids:
      node = node_manager.nodes[child_id]
      nodes_used.add(node)

    groups.append(parent)
    if not is_dev:
      remaining = text_nodes.difference(nodes_used)
  return groups

def try_create_fraction(
  node_manager: nodemanager.NodeManager,
  node: pdftypes.ClassificationNode,
  nodes_used: typing.Set[pdftypes.ClassificationNode]
):
  if node in nodes_used:
    return None
  query = make_query_square(node=node, radius=max(node.width(), node.height()))

  neighors = node_manager.intersection(layer_idx=1, bbox=query)
  neighors = [ n for n in neighors if n.node_id != node.node_id and n not in nodes_used ]
  neighors.sort(key=lambda n: pdfelemtransforms.get_node_distance_to(other=n, src=node))
  int_neighbors = [
    n for n in neighors if \
      n.labels[pdftypes.LabelType.INT] > 0 and \
      n.left_right == node.left_right and \
      abs(n.fontsize - node.fontsize) < FONT_SIZE_DIFF
  ]
  dividor_neighbors = [n for n in neighors if n.labels[pdftypes.LabelType.FRACTION_LINE] > 0]
  if not node.left_right:
    for n in neighors:
      if abs(n.length - node.height()) < node.height():
        if abs(abs(n.slope) - path_utils.MAX_SLOPE) < 10:
          dividor_neighbors.append(n)
  for dividor_node in dividor_neighbors:
    def dividor_similar_sized(
      dividor_node: pdftypes.ClassificationNode,
      int_node: pdftypes.ClassificationNode
    ):
      size = max(int_node.width(), int_node.height())
      if abs(dividor_node.length - size) < size:
        return True
    def dividor_is_between(
      node: pdftypes.ClassificationNode,
      int_node: pdftypes.ClassificationNode,
      dividor_node: pdftypes.ClassificationNode
    ):
      int_to_int_dist = pdfelemtransforms.get_node_midpoint_distance_to(
        other=int_node,
        src=node
      )
      int_to_dividor_dist = pdfelemtransforms.get_node_midpoint_distance_to(
        other=int_node,
        src=dividor_node,
      )
      return int_to_dividor_dist < int_to_int_dist

    dividor_matches_node_size = dividor_similar_sized(dividor_node=dividor_node, int_node=node)
    rel_angle = pdfelemtransforms.get_node_angle_to(
      other=dividor_node,
      src=node,
    )
    ints_in_dir = pdfelemtransforms.get_nodes_in_direction_from(
      others=int_neighbors,
      src=node,
      angle=rel_angle,
      threshold=10
    )

    ints_in_dir = [
      n for n in ints_in_dir if \
        dividor_matches_node_size or \
        dividor_similar_sized(dividor_node=dividor_node, int_node=n)
    ]
    ints_in_dir = [
      n for n in ints_in_dir if dividor_is_between(node=node, int_node=n, dividor_node=dividor_node)
    ]
    if len(ints_in_dir) > 0:
      other_int = ints_in_dir[0]
      if node.left_right:
        if abs(abs(rel_angle)-0) < 10:
          # other_int
          # ---------
          #   node
          return [other_int, dividor_node, node]
        elif abs(abs(rel_angle) - 180) < 10:
          #   node
          # ---------
          # other_int
          return [node, dividor_node, other_int]
        elif rel_angle < 0:
          # other_int / node
          return [other_int, dividor_node, node]
        else:
          # node / other_int
          return [node, dividor_node, other_int]
      else:
        if node.bbox[0] < other_int.bbox[0]:
          return [ node, dividor_node, other_int ]
        return [ other_int, dividor_node, node ]
  return None

def cluster_fractions(
  node_manager: nodemanager.NodeManager,
  groups: typing.List[pdftypes.ClassificationNode],
):
  nodes_used: typing.Set[pdftypes.ClassificationNode] = set()
  fractions_clustered: typing.List[pdftypes.ClassificationNode] = []
  for node in groups:
    if node.labels[pdftypes.LabelType.INT] > 0:
      fraction_group = try_create_fraction(
        node_manager=node_manager,
        node=node,
        nodes_used=nodes_used,
      )
      if fraction_group is not None:
        for n in fraction_group:
          nodes_used.add(n)
        out_text = pdfelemtransforms.join_text_line(nodes=fraction_group)
        bounding_bbox = pdfelemtransforms.bounding_bbox(elems=fraction_group)
        child_ids = [n.node_id for n in fraction_group]
        group_parent = node_manager.add_node(
          elem=None,
          bbox=bounding_bbox,
          line=None,
          text=out_text,
          left_right=node.left_right,
          child_ids=child_ids,
          layer_id=2,
        )
        group_parent.labelize()
        fractions_clustered.append(group_parent)

  return fractions_clustered

def node_should_add_to_group_join_fractions(
  processing: pdftypes.ClassificationNode,
  node: pdftypes.ClassificationNode,
  group: typing.Set[pdftypes.ClassificationNode],
):
  if node in group:
    return False
  node.labelize()
  if node.text is not None:
    if node.left_right != processing.left_right:
      return False

    idx0, idx1 = pdfelemtransforms.get_idx_for_vert(vert=processing.left_right)

    perpendicular_overlap = pdfelemtransforms.get_overlap_in_direction(
      this=processing.bbox,
      other=node.bbox,
      height_overlap=processing.left_right,
    )
    if processing.labels[pdftypes.LabelType.FRACTION] > 0 or node.labels[pdftypes.LabelType.FRACTION] > 0:
      start_perpendicular_size = processing.height() if processing.left_right else processing.width()
      if perpendicular_overlap / start_perpendicular_size > 0.25:
        # Enough overlap
        if processing.bbox[idx0] < node.bbox[idx0] and processing.bbox[idx1] > node.bbox[idx1]:
          # node centered inside processing
          return True
        elif processing.bbox[idx0] > node.bbox[idx0] and processing.bbox[idx1] < node.bbox[idx1]:
          # processing centered inside node
          return True
  return False

def cluster_fractions_with_text(
  node_manager: nodemanager.NodeManager,
  fractions: typing.List[pdftypes.ClassificationNode],
  source_layer_idx: int,
):
  nodes_used: typing.Set[
    pdftypes.ClassificationNode,
  ] = set()
  fractions_set = set(fractions)
  remaining = fractions_set.difference(nodes_used)
  groups: typing.List[pdftypes.ClassificationNode] = []
  while len(remaining) > 0:
    start_node = remaining.pop()

    parent = cluster_text_group(
      node_manager=node_manager,
      start=start_node,
      source_layer_idx=source_layer_idx,
      node_should_add_to_group_func=node_should_add_to_group_join_fractions,
    )
    for child_id in parent.child_ids:
      node = node_manager.nodes[child_id]
      nodes_used.add(node)

    groups.append(parent)
    remaining = fractions_set.difference(nodes_used)
  return groups

def cluster_text(
  node_manager: nodemanager.NodeManager,
):
  split_space = False
  if split_space:
    groups = cluster_text_by_connected_groups(
      node_manager=node_manager,
      source_layer_idx=0,
      node_should_add_to_group_func=node_should_add_to_group_split_space,
    )
  else:
    groups = cluster_text_by_connected_groups(
      node_manager=node_manager,
      source_layer_idx=0,
      node_should_add_to_group_func=node_should_add_to_group_join_space,
    )
  node_manager.index_layer(layer_idx=1)
  print("Got groups", len(groups))
  fractions = cluster_fractions(
    node_manager=node_manager,
    groups=groups,
  )
  node_manager.index_layer(layer_idx=2)
  print("Num fractions:", len(fractions))
  fraction_text_groups = cluster_fractions_with_text(
    node_manager=node_manager,
    fractions=fractions,
    source_layer_idx=2,
  )

  print("Fraction groups:", len(fraction_text_groups))
  joined_whitespace_groups = None # type: ignore
  if split_space:
    # join space at step 1
    # 804    0.045    0.000    1.137    0.001 test.py:874(cluster_text_group)
    # keep space divided
    # 2403    0.076    0.000    1.846    0.001 test.py:874(cluster_text_group)
    # join space at last step
    # 4565    0.368    0.000    9.501    0.002 test.py:874(cluster_text_group)
    # 115782    0.145    0.000    4.804    0.000 pdftypes.py:329(intersection)
    node_manager.index_layer(layer_idx=3)
    joined_whitespace_groups = cluster_text_by_connected_groups( # type: ignore
      node_manager=node_manager,
      source_layer_idx=3,
      node_should_add_to_group_func=node_should_add_to_group_join_space,
    )
  else:
    # Vs: 1    0.000    0.000    1.748    1.748 test.py:1151(conn_test)
    last_layer_nodes = [node_manager.nodes[node_id] for node_id in node_manager.layers[3]]
    text_nodes = [n for n in last_layer_nodes if n.text is not None]
    for n in text_nodes:
      if n.text is not None:
        splits = n.text.split(" ") # type: ignore


  return groups, fractions, fraction_text_groups
