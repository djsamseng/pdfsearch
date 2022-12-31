

import typing

import pdfminer, pdfminer.layout, pdfminer.high_level

import pdfdrawer

ElemListType = typing.List[typing.Union[pdfminer.layout.LTCurve, pdfminer.layout.LTChar]]
BboxType = typing.Tuple[float, float, float, float]

def extend_out_if_element(out: ElemListType, elem: typing.Union[None, list, pdfminer.layout.LTCurve, pdfminer.layout.LTChar]):
  if elem == None:
    return
  elif isinstance(elem, list):
    out.extend(elem)
  elif isinstance(elem, pdfminer.layout.LTCurve):
    out.append(elem)
  elif isinstance(elem, pdfminer.layout.LTChar):
    out.append(elem)
  else:
    print("Unhandled extend:", elem)

def get_underlying_from_element(elem: pdfminer.layout.LTComponent) -> typing.Union[None, list, pdfminer.layout.LTCurve, pdfminer.layout.LTChar]:
  if isinstance(elem, pdfminer.layout.LTTextLineHorizontal):
    out = []
    for sub_elem in elem:
      extend_out_if_element(out=out, elem=get_underlying_from_element(sub_elem))
    return out
  elif isinstance(elem, pdfminer.layout.LTTextBoxHorizontal):
    out = []
    for sub_elem in elem:
      extend_out_if_element(out=out, elem=get_underlying_from_element(sub_elem))
    return out
  elif isinstance(elem, pdfminer.layout.LTTextContainer):
    print(elem)
    assert False, "Unhandled LTTextContainer" + str(elem)
  elif isinstance(elem, pdfminer.layout.LTChar):
    return elem
  elif isinstance(elem, pdfminer.layout.LTAnno):
    return None
  elif isinstance(elem, pdfminer.layout.LTCurve):
    return elem
  elif isinstance(elem, pdfminer.layout.LTLine):
    # LTLine and LTRect is a LTCurve
    print("Line:", elem.pts, elem.fill, elem.stroking_color, elem.stroke, elem.non_stroking_color, elem.evenodd, elem.linewidth)
    assert False, "Unhandled line:" + str(elem)
  else:
    print("Unhandled:", elem)
    assert False, "Unhandled elem:" + str(elem)

def get_underlying(page: pdfminer.layout.LTPage) -> ElemListType:
  out: ElemListType = []
  for elem in page:
    extend_out_if_element(out=out, elem=get_underlying_from_element(elem=elem))
  return out

def extract_window_schedule_test():
  page_gen = pdfminer.high_level.extract_pages(pdf_file="../plan.pdf", page_numbers=[3-1])
  page = next(iter(page_gen))

  drawer = pdfdrawer.FitzDraw(width=page.width, height=page.height)
  elems = get_underlying(page=page)
  pdfdrawer.draw_elems(elems=elems, drawer=drawer)
  drawer.show("Window Schedule")

  y0, x0 = 968, 958
  y1, x1 = 2100, 1865
  bbox = (x0, page.height-y1, x1, page.height-y0)

  pdfdrawer.waitKey(0)

def main():
  extract_window_schedule_test()

if __name__ == "__main__":
  main()