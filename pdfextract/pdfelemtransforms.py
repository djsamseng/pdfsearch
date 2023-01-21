
import json
import typing

import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils

from .ltjson import LTJson, BboxType, LTJsonEncoder

def get_underlying_parent_links_impl(
  out: typing.List[LTJson],
  elem: pdfminer.layout.LTComponent,
  elem_parent_idx: typing.Union[None, int],
):
  if isinstance(elem, pdfminer.layout.LTContainer):
    # Add the container
    out.append(
      LTJson(
        elem=typing.cast(pdfminer.layout.LTComponent, elem),
        parent_idx=elem_parent_idx
      )
    )
    if isinstance(elem, pdfminer.layout.LTText):
      # takes 20ms out of 150ms
      text = elem.get_text()
      out[-1].text = text
    child_parent_idx = len(out) - 1 # Get the container's idx
    for child in typing.cast(typing.Iterable[pdfminer.layout.LTComponent], elem):
      # Add the first child
      # Get the first child's idx
      # Add the first child's children - recurse
      get_underlying_parent_links_impl(out=out, elem=child, elem_parent_idx=child_parent_idx)
  elif isinstance(elem, pdfminer.layout.LTChar):
    if elem_parent_idx is None:
      print("LTChar without parent:", elem, elem_parent_idx)
    out.append(LTJson(elem, parent_idx=elem_parent_idx))
  elif isinstance(elem, pdfminer.layout.LTAnno):
    text = elem.get_text()
    if text != "\n" and text != " ":
      print("Unhandled LTAnno", elem)
    # Not Added
  elif isinstance(elem, pdfminer.layout.LTCurve):
    out.append(LTJson(elem, parent_idx=elem_parent_idx))
  elif isinstance(elem, pdfminer.layout.LTFigure):
    # Not Added
    print("Unhandled figure", elem)
  elif isinstance(elem, pdfminer.layout.LTImage):
    # TODO: Notify user pdf images not searched
    pass
  else:
    print("Unhandled elem:", elem)

def get_underlying_parent_links(
  elems: typing.Iterable[pdfminer.layout.LTComponent],
):
  out: typing.List[LTJson] = []
  for elem in elems:
    get_underlying_parent_links_impl(out=out, elem=elem, elem_parent_idx=None)
  return out

def box_contains(outer: BboxType, inner: BboxType):
  x0a, y0a, x1a, y1a = outer
  x0b, y0b, x1b, y1b = inner
  if x0a <= x0b and y0a <= y0b:
    # outer starts before inner
    if x1a >= x1b and y1a >= y1b:
      # outer ends after inner
      return True
  return False

def filter_contains_bbox_hierarchical(elems: typing.Iterable[LTJson], bbox: BboxType) -> typing.List[LTJson]:
  out: typing.List[LTJson] = []
  json_encoder = LTJsonEncoder()
  old_idx_to_new_idx: typing.Dict[int, int] = dict()
  for old_idx, wrapper in enumerate(elems):
    new_parent_idx = None
    if wrapper.parent_idx is not None:
      if wrapper.parent_idx in old_idx_to_new_idx:
        new_parent_idx = old_idx_to_new_idx[wrapper.parent_idx]
    if wrapper.is_annotation:
      continue
    if box_contains(outer=bbox, inner=wrapper.bbox):
      elem_copy = LTJson(serialized_json=json.loads(json_encoder.encode(wrapper)))
      elem_copy.parent_idx = new_parent_idx
      out.append(elem_copy)
      old_idx_to_new_idx[old_idx] = len(out) - 1

  return out
