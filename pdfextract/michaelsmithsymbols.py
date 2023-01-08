
import argparse

import pdfminer.high_level

import pdfextracter
import pdftkdrawer

def get_construction_plan_notes_circle():
  y0, x0 = 1559, 1831
  y1, x1 = 1588, 1859

def get_window_label_symbol():
  y0, x0 = 1755, 1393
  y1, x1 = 1781, 1417

def get_window_symbol():
  y0, x0 = 1695, 1366
  y1, x1 = 1802, 1391

def get_door_label_symbol():
  y0, x0 = 1458, 894
  y1, x1 = 1480, 924

def get_door_symbol():
  y0, x0 = 1459, 882
  y1, x1 = 1511, 938

def get_sink_symbol():
  y0, x0 = 1716, 1039
  y1, x1 = 1750, 1066

def get_toilet_symbol():
  y0, x0 = 858, 258
  y1, x1 = 909, 288

def get_pdf():
  page_gen = pdfminer.high_level.extract_pages(pdf_file="../plan.pdf", page_numbers=[9])
  pages = list(page_gen)
  page = pages[0]
  width = int(page.width)
  height = int(page.height)
  elem_wrappers = pdfextracter.get_underlying_parent_links(elems=page)

  print(len(elem_wrappers), width, height)
  elem_wrappers = elem_wrappers[:5000]
  drawer = pdftkdrawer.TkDrawer(width=width, height=height)
  drawer.draw_elems(elems=elem_wrappers)
  drawer.show("First Floor Construction Plan")

def get_all_symbols():
  get_pdf()

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--windowsymbol", dest="windowsymbol", default=False, action="store_true")
  return parser.parse_args()

# Locate symbols by running flaskapi/pdfdrawer.py
def main():
  get_all_symbols()

if __name__ == "__main__":
  main()