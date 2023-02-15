
import collections
import typing

import rtree

from . import pdftypes, path_utils

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

T = typing.TypeVar("T", pdftypes.LineSymbol, pdftypes.TextSymbol)
class SymbolIndexer(typing.Generic[T]):
  ReturnType = typing.Tuple[int, int]
  def __init__(
    self,
    sym_to_coords: typing.Callable[[T], pdftypes.Bbox],
  ) -> None:
    self.symbols: typing.List[T] = []
    self.return_ids: typing.List[typing.List[SymbolIndexer.ReturnType]] = []
    self.rtree = rtree.index.Index()
    self.sym_to_coords = sym_to_coords
    self.indexer: SingletonIndexer[SymbolIndexer.ReturnType] = SingletonIndexer()

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

class ShapeManager:
  def __init__(
    self,
  ) -> None:
    self.indexer = SymbolIndexer(
      sym_to_coords=line_symbol_to_coords
    )
    self.dslope = 0.1
    self.dlength = 0.5
    self.shape_start_radius = 0.5
    self.weights = {
      pdftypes.ClassificationType.SLOPE: 1.,
      pdftypes.ClassificationType.LENGTH: 1.,
    }
    self.shapes: typing.List[
      typing.Tuple[
        typing.List[pdftypes.LineSymbol],
        typing.List[path_utils.OffsetType]
      ]
    ] = []
    # Shape = [lines], [offsets]
    # Found shape = x0, y0, [lines], [offsets]
    # Activations[(x0,y0)][shape_id][line_id] = score
    self.activation_lookup: SingletonIndexer[
      typing.Tuple[int, int, float, pdftypes.ClassificationNode]
    ] = SingletonIndexer()


  def add_shape(
    self,
    lines: typing.List[path_utils.LinePointsType],
  ):
    bounding_box = path_utils.lines_bounding_bbox(elems=lines)
    shape_id = len(self.shapes)
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
    self.shapes.append(shape)

  def activate_leaf(
    self,
    node: pdftypes.ClassificationNode
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
        self.activation_lookup.add(coords=coords, to_return=(shape_id, line_id, activation, node))

  def get_activations(self):

    nodes_used: typing.List[pdftypes.ClassificationNode] = []
    for idx, shape_start in enumerate(self.activation_lookup.stored):
      pending_nodes: typing.List[pdftypes.ClassificationNode] = []
      activations: typing.DefaultDict[
        int, # shape_id
        typing.DefaultDict[
          int, # line_id
          typing.List[float],
        ]
      ] = collections.defaultdict(lambda: collections.defaultdict(list))
      x0, y0, _, _ = self.activation_lookup.coords[idx]
      x0 += self.shape_start_radius
      y0 += self.shape_start_radius
      for shape_id, line_id, activation, node in shape_start:
        activations[shape_id][line_id].append(activation)
        if activation > 0.9:
          pending_nodes.append(node)

      for shape_id, shape_lines in activations.items():
        shape_score = sum([max(l) for l in shape_lines.values()])
        shape_total = len(self.shapes[shape_id][0])
        shape_activation = shape_score / shape_total
        if shape_activation > 0.9:
          # TODO: Return x0, y0, self.shapes[shape_id]
          print("id:", shape_id, "score:", shape_score, "/", shape_total, "at:", (x0, y0))
          nodes_used.extend(pending_nodes)
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

class TextSymbolIndexer:
  def __init__(
    self,
    symbols: typing.List[pdftypes.TextSymbol]
  ) -> None:
    self.indexer = SymbolIndexer(
      symbols=symbols,
      sym_to_coords=text_symbol_to_coords,
    )

  def intersection(
    self,
    text: str,
    size: float,
    dsize: float,
  ) -> typing.Iterator[int]:
    x0 = str_to_coord(s=text)
    x1 = x0
    y0 = size - dsize
    y1 = size + dsize
    return self.indexer.intersection(coords=(x0, y0, x1, y1))
