
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

  def add(
    self,
    symbol: T,
    return_id: ReturnType,
  ):
    x0, y0, x1, y1 = self.sym_to_coords(symbol)
    idxes = self.rtree.intersection((x0, y0, x1, y1), objects=False)
    idxes = list(idxes)
    if len(idxes) > 0:
      for symbol_idx in idxes:
        self.return_ids[symbol_idx].append(return_id)
    else:
      symbol_idx = len(self.symbols)
      self.rtree.add(symbol_idx, (x0, y0, x1, y1), None)
      self.symbols.append(symbol)
      self.return_ids.append([return_id])

  def intersection(
    self,
    x0:float,
    y0:float,
    x1:float,
    y1:float
  ) -> typing.List[typing.List[ReturnType]]:
    # return the symbol and the offset
    # multiple offsets per symbol
    idxes = self.rtree.intersection((x0, y0, x1, y1), objects=False)
    return [ self.return_ids[idx] for idx in idxes ] #pylint: disable=not-an-iterable

class ShapeManager:
  def __init__(
    self,
  ) -> None:
    self.indexer = SymbolIndexer(
      sym_to_coords=line_symbol_to_coords
    )
    self.dslope = 0.1
    self.dlength = 0.5
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
    self.activations: typing.DefaultDict[
      typing.Tuple[float, float], # (x0, y0)
      typing.DefaultDict[
        int, # shape_id
        typing.Dict[
          int, # line_id
          float
        ]
      ]
    ] = collections.defaultdict(lambda: collections.defaultdict(dict))

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
    print("====")
    # Maybe the slope is reversed?
    # 2.2258065838951044e-05 (1125.72, 839.3399999999999)
    # 1.5177679542674058e-05 (1125.72, 839.3399999999999)
    # 1.0 (1125.72, 839.3399999999999)
    for leaf_match in matches:
      for shape_id, line_id in leaf_match:
        line_symbol = self.shapes[shape_id][0][line_id]
        offset = self.shapes[shape_id][1][line_id]
        x0 = node.line[0] - offset[0]
        y0 = node.line[1] - offset[1]
        activation = line_symbol.activation(node=node, weights=self.weights)
        # 1.0 (1125.72, 839.3399999999999)
        print(activation, (x0, y0))
        self.activations[(x0, y0)][shape_id][line_id] = activation

  def get_activations(self):
    for (x0, y0), shapes_dict in self.activations.items():
      for shape_id in shapes_dict.keys():
        shape_score = sum(shapes_dict[shape_id].values())
        shape_total = len(self.shapes[shape_id][0])
        print(shape_score, "/", shape_total, "at:", (x0, y0))

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
    return self.indexer.intersection(x0=x0, y0=y0, x1=x1, y1=y1)

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
    return self.indexer.intersection(x0=x0, y0=y0, x1=x1, y1=y1)
