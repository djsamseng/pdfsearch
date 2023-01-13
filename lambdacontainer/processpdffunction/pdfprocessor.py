
import io
import typing

import pdfminer, pdfminer.pdfparser, pdfminer.pdfdocument, pdfminer.pdftypes, pdfminer.layout, pdfminer.high_level, pdfminer.utils

import dataprovider
import debugutils
from pdfextract import pdfindexer, pdfextracter

def get_pdf_num_pages(pdfdata_io: io.BytesIO):
  parser = pdfminer.pdfparser.PDFParser(pdfdata_io)
  document = pdfminer.pdfdocument.PDFDocument(parser)
  num_pages = pdfminer.pdftypes.resolve1(document.catalog["Pages"])["Count"]
  return num_pages

class PdfProcessor:
  def __init__(self, pages_gen: typing.Iterator[pdfminer.layout.LTPage]) -> None:
    self.pages_gen = pages_gen

  def process_page(self):
    for page in self.pages_gen:
      width = page.width
      height = page.height
      elems = pdfextracter.get_underlying_parent_links(elems=page)
      indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)
      print("Indexer:", indexer)
      yield

def process_pdf(pdfkey:str, pdfdata: bytes):
  pdfdata_io = io.BytesIO(initial_bytes=pdfdata)
  num_pages = get_pdf_num_pages(pdfdata_io=pdfdata_io)
  num_steps_total = num_pages + 1
  dataprovider.write_processpdf_start(pdfkey=pdfkey, num_steps_total=num_steps_total)

  if debugutils.is_dev():
    pages_gen = pdfminer.high_level.extract_pages(pdf_file=pdfdata_io, page_numbers=[9])
  else:
    pages_gen = pdfminer.high_level.extract_pages(pdf_file=pdfdata_io)
  processor = PdfProcessor(pages_gen=pages_gen)
  for idx, _ in enumerate(processor.process_page()):
    dataprovider.write_processpdf_progress(pdfkey=pdfkey, curr_step=idx+1, message="Processing page: {0}".format(idx+1))
