
import collections
import re
import typing

import rtree

from . import pdftypes, path_utils, leafgrid, pdfelemtransforms

import pdfminer.layout

def line_symbol_to_coords(sym: pdftypes.LineSymbol):
  x = sym.slope
  y = sym.length
  return (x, y, x, y)

def char_to_int(char: str):
  ord_val = ord(char.lower())
  if 97 <= ord_val and ord_val <= 122:
    return ord_val - 97 + 1 # [1,26]
  elif 48 <= ord_val and ord_val <= 57:
    return ord_val - 48 + 27 # [27,37]

  if char == "\n":
    return 38
  elif char == "!":
    return 39
  elif char == "/":
    return 40

  return 0

def str_to_coord(s: str) -> float:
  return sum([char_to_int(c) * (10 ** idx) for idx, c in enumerate(s)])

def text_symbol_to_coords(sym: pdftypes.TextSymbol):
  # TODO: sinusoidal embedding
  x = str_to_coord(sym.text)
  y = sym.width + sym.height
  return x, y, x, y

S = typing.TypeVar("S")
class SingletonIndexer(typing.Generic[S]):
  def __init__(self) -> None:
    self.rtree = rtree.index.Index()
    self.stored: typing.List[typing.List[S]] = []
    self.coords: typing.List[pdftypes.Bbox] = []

  def add(
    self,
    coords: path_utils.Bbox,
    to_return: S,
  ):
    idxes = self.rtree.intersection(coordinates=coords, objects=False)
    idxes = list(idxes)
    if len(idxes) > 0:
      for match_idx in idxes:
        self.stored[match_idx].append(to_return)
    else:
      idx = len(self.stored)
      self.rtree.add(idx, coordinates=coords, obj=None)
      self.stored.append([to_return])
      self.coords.append(coords)

  def intersection(
    self,
    coords: path_utils.Bbox,
  ) -> typing.List[typing.List[S]]:
    idxes = self.rtree.intersection(coordinates=coords, objects=False)
    results = [ self.stored[idx] for idx in idxes] #pylint: disable=not-an-iterable
    return results




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
      lines = [
        self.layer_nodes[idx] for idx in lines_idxes if self.layer_nodes[idx].line is not None
      ]
      upright = node.upright
      if not upright:
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
      joined_node.upright = upright
      return joined_node
    else:
      idx = len(self.nodes)
      self.join_rtree.add(idx, coordinates=node.bbox, obj=None)
      self.nodes.append(node)
      node_ids_stranded.add(idx)
      return None

T = typing.TypeVar("T", pdftypes.LineSymbol, pdftypes.TextSymbol)
ReturnType = typing.TypeVar("ReturnType")
class SymbolIndexer(typing.Generic[T, ReturnType]):
  def __init__(
    self,
    sym_to_coords: typing.Callable[[T], pdftypes.Bbox],
  ) -> None:
    self.symbols: typing.List[T] = []
    self.return_ids: typing.List[typing.List[ReturnType]] = []
    self.rtree = rtree.index.Index()
    self.sym_to_coords = sym_to_coords
    self.indexer: SingletonIndexer[ReturnType] = SingletonIndexer()

  def add(
    self,
    symbol: T,
    return_id: ReturnType,
  ):
    self.indexer.add(
      coords=self.sym_to_coords(symbol),
      to_return=return_id)

  def intersection(
    self,
    coords: pdftypes.Bbox,
  ) -> typing.List[typing.List[ReturnType]]:
    # return the symbol and the offset
    # multiple offsets per symbol
    return self.indexer.intersection(coords=coords)

ShapeActivationPosition = typing.DefaultDict[
  int, # shape_id
  typing.Dict[
    int, # line_id
    float
  ]
]
ShapeActivations = typing.DefaultDict[
  path_utils.OffsetType,
  ShapeActivationPosition
]

def insertion_generator(nodes: typing.List[pdftypes.ClassificationNode]):
  for node_idx, node in enumerate(nodes):
    yield (node_idx, node.bbox, None)

ActivationLookupType = SingletonIndexer[typing.Tuple[str, int, float, pdftypes.ClassificationNode]]
class ShapeManager:
  def __init__(
    self,
    node_manager: pdftypes.NodeManager,
  ) -> None:
    self.node_manager = node_manager
    self.indexer: SymbolIndexer[
      pdftypes.LineSymbol,
      typing.Tuple[str, int]
    ] = SymbolIndexer(
      sym_to_coords=line_symbol_to_coords
    )
    self.dslope = 0.1
    self.dlength = 0.5
    self.shape_start_radius = 0.5
    self.weights = {
      pdftypes.ClassificationType.SLOPE: 1.,
      pdftypes.ClassificationType.LENGTH: 1.,
    }
    self.shapes: typing.Dict[
      str,
      typing.Tuple[
        typing.List[pdftypes.LineSymbol],
        typing.List[path_utils.OffsetType]
      ]
    ] = {}

    self.results: typing.DefaultDict[
      str, # shape_id
      typing.List[pdftypes.ClassificationNode]
    ] = collections.defaultdict(list)

  # TODO: Extend to more general entities
  # For text offsets work for joining characters
  # but we really want to move to a grid model where we join the grid
  # as we join the grid, shapes/entities start to activate
  # Activations show us how to join the grid
  # EX: "W", "WI", "WIN", "WINDOW" - seeing a character makes us look to what is right
  # EX: "A01" makes us look for a window symbol or to see if it's in a table
  # EX: "BATHROOM" makes us look for the room boundary, sinks, etc.
  # 1. Loop over all elems and assign priorities (ie sort)
  #   - Text probably has the highest priority
  #   - Large text first
  #   - lines/rectangles are more for dividing lines than joining
  # 2. Join characters into words and assign word priorities
  #   - Ex: "BAR" has a "Indicates Center Line" line through it
  # 3. Look for "WINDOW SCHEDULE", parse out the table.
  #   - Now we have more entities to search for (ShapeSymbols and LineSymbols)
  def add_shape(
    self,
    shape_id: str,
    lines: typing.List[path_utils.LinePointsType],
  ):
    bounding_box = path_utils.lines_bounding_bbox(elems=lines)
    shape: typing.Tuple[
      typing.List[pdftypes.LineSymbol],
      typing.List[path_utils.OffsetType]
    ] = ([], [])
    for line_id, line in enumerate(lines):
      line_symbol = pdftypes.LineSymbol(line=line)
      offset = (line[0] - bounding_box[0], line[1] - bounding_box[1],)
      self.indexer.add(symbol=line_symbol, return_id=(shape_id, line_id,))
      shape[0].append(line_symbol)
      shape[1].append(offset)
    self.shapes[shape_id] = shape

  def activate_layers(self):
    nodes_used: typing.List[pdftypes.ClassificationNode] = []
    old_layers = []
    new_layers = list(self.node_manager.layers.keys())
    while len(old_layers) != len(new_layers):
      old_layers = list(self.node_manager.layers.keys())
      for layer_id in old_layers:
        used_in_layer = self.__activate_layer(layer_id=layer_id)
        nodes_used.extend(used_in_layer)
      new_layers = list(self.node_manager.layers.keys())

    return nodes_used

  def __activate_layer(self, layer_id: int) -> typing.List[pdftypes.ClassificationNode]:
    # Layer 0 is chars and lines
    # Layer 1 is words and shapes/rects
    # Layer 2 is text inside shapes / text inside schedules / text inside measurement lines
    # Layer 3 is shapes inside shapes / rooms
    # Layer 4 is sections of the page / different floors on the same page
    if layer_id == 0:
      return self.__activate_leaf_layer(layer_id=layer_id)
    return []

  def __activate_leaf_layer(self, layer_id: int):
    layer_node_ids = self.node_manager.layers[layer_id]
    layer = [self.node_manager.nodes[node_id] for node_id in layer_node_ids]
    nodes_used: typing.List[pdftypes.ClassificationNode] = []
    # Shape = [lines], [offsets]
        # Found shape = x0, y0, [lines], [offsets]
        # Activations[(x0,y0)][shape_id][line_id] = score
    activation_lookup: ActivationLookupType = SingletonIndexer()
    for node in layer:
      if len(node.parent_ids) > 0:
        continue
      if node.line is not None:
        self.__activate_line_leaf(node=node, activation_lookup=activation_lookup)
      if node.text is not None:
        # TODO: Join text
        # Keep a pending joined layer
        # Check for text around me in the pending joined layer
        # If so join and replace in pending joined layer
        # Else add solo char to pending joined layer
        pass
    nodes_used = self.__join_layer(
      activation_lookup=activation_lookup,
      next_layer_id=layer_id + 1,
    )
    # Align, walk, box
    # 1. Find text bbox and snap to the beginning of the next
    #    - divide into smaller regions, we may transfer a region to a different group
    #    - use the leafgrid to find large areas of whitespace
    # 2. Walk in the direction of the text
    #    - join the smaller regions
    # 3. Narrow the final bbox
    # 4. Repeat for all areas
    text_joiner = TextJoiner(
      layer_nodes=[self.node_manager.nodes[node_id] for node_id in self.node_manager.layers[0]],
      layer_rtree=self.node_manager.indexes[0],
    )

    joined_text_nodes = text_joiner.join()
    print([n.text for n in joined_text_nodes])
    return nodes_used

  def __activate_line_leaf(
    self,
    node: pdftypes.ClassificationNode,
    activation_lookup: ActivationLookupType,
  ):
    if node.line is None:
      return
    # activate leafs
    matches = self.__intersection(
      line_slope=node.slope,
      line_length=node.length,
      dslope=self.dslope,
      dlength=self.dlength)
    for leaf_match in matches:
      for shape_id, line_id in leaf_match:
        line_symbol = self.shapes[shape_id][0][line_id]
        offset = self.shapes[shape_id][1][line_id]
        activation = line_symbol.activation(node=node, weights=self.weights)
        x0 = node.line[0] - offset[0]
        y0 = node.line[1] - offset[1]
        coords=(
          x0 - self.shape_start_radius,
          y0 - self.shape_start_radius,
          x0 + self.shape_start_radius,
          y0 + self.shape_start_radius,
        )
        activation_lookup.add(coords=coords, to_return=(shape_id, line_id, activation, node))

  def __join_layer(
    self,
    activation_lookup: ActivationLookupType,
    next_layer_id: int,
  ):
    nodes_used: typing.List[pdftypes.ClassificationNode] = []
    for idx, shape_start in enumerate(activation_lookup.stored):
      activations: typing.DefaultDict[
        str, # shape_id
        typing.Dict[
          int, # line_id
          typing.Tuple[float, pdftypes.ClassificationNode],
        ]
      ] = collections.defaultdict(dict)
      x0, y0, _, _ = activation_lookup.coords[idx]
      x0 += self.shape_start_radius
      y0 += self.shape_start_radius
      for shape_id, line_id, activation, node in shape_start:
        if line_id in activations[shape_id]:
          if activation > activations[shape_id][line_id][0]:
            activations[shape_id][line_id] = (activation, node)
        else:
          activations[shape_id][line_id] = (activation, node)

      for shape_id, shape_lines in activations.items():
        shape_nodes = [ t[1] for t in shape_lines.values() ]
        shape_score = sum([t[0] for t in shape_lines.values()])
        shape_total = len(self.shapes[shape_id][0])
        shape_activation = shape_score / shape_total
        if shape_activation > 0.9:
          if next_layer_id not in self.node_manager.layers:
            self.node_manager.create_layer(layer_id=next_layer_id)
          child_ids = [ n.node_id for n in shape_nodes ]
          shape_bbox = path_utils.lines_bounding_bbox(
            elems=[ n.line for n in shape_nodes if n.line is not None ],
          )
          new_parent = self.node_manager.add_node(
            elem=None,
            bbox=shape_bbox,
            line=None,
            text=None,
            child_ids=child_ids,
            layer_id=next_layer_id
          )
          for node in shape_nodes:
            node.parent_ids.add(new_parent.node_id)
          print("id:", shape_id, "score:", shape_score, "/", shape_total, "at:", (x0, y0))
          nodes_used.extend(shape_nodes)
          self.results[shape_id].append(new_parent)
    return nodes_used

  def __intersection(
    self,
    line_slope:float,
    line_length:float,
    dslope:float,
    dlength:float
  ):
    x0 = line_slope - dslope
    x1 = line_slope + dslope
    y0 = line_length - dlength
    y1 = line_length + dlength
    return self.indexer.intersection(coords=(x0, y0, x1, y1))

