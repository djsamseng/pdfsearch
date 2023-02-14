
import typing

import rtree

from . import pdftypes

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
  def __init__(
    self,
    symbols: typing.List[T],
    sym_to_coords: typing.Callable[[T], pdftypes.Bbox],
  ) -> None:
    self.symbols = symbols
    self.sym_to_coords = sym_to_coords
    def insertion_generator(symbols: typing.List[T]):
      for idx, sym in enumerate(symbols):
        x0, y0, x1, y1 = self.sym_to_coords(sym)
        yield (idx, (x0, y0, x1, y1), None)
    self.rtree = rtree.index.Index(
      insertion_generator(symbols=symbols)
    )
  def intersection(
    self,
    x0:float,
    y0:float,
    x1:float,
    y1:float
  ) -> typing.List[T]:
    idxes = self.rtree.intersection((x0, y0, x1, y1), objects=False)
    return [ self.symbols[idx] for idx in idxes ] #pylint: disable=not-an-iterable

class LineSymbolIndexer:
  def __init__(
    self,
    symbols: typing.List[pdftypes.LineSymbol],
  ) -> None:
    self.indexer = SymbolIndexer(
      symbols=symbols,
      sym_to_coords=line_symbol_to_coords,
    )

  def intersection(
    self,
    line_slope:float,
    line_length:float,
    dslope:float,
    dlength:float
  ) -> typing.List[pdftypes.LineSymbol]:
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
  ):
    x0 = str_to_coord(s=text)
    x1 = x0
    y0 = size - dsize
    y1 = size + dsize
    return self.indexer.intersection(x0=x0, y0=y0, x1=x1, y1=y1)
