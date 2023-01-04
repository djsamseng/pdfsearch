
import typing
import pdfminer, pdfminer.layout

def print_elem_tree(elems: typing.Iterable[pdfminer.layout.LTComponent], depth: int=0):
  for elem in elems:
    print("".ljust(depth, "-"), elem)
    if isinstance(elem, pdfminer.layout.LTContainer):
      print_elem_tree(elems=typing.cast(typing.Iterable[pdfminer.layout.LTComponent], elem), depth=depth+1)