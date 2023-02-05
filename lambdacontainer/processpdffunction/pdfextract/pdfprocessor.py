
import io
import json
import os
import typing
import time

import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils
import pdfminer.pdfparser, pdfminer.pdfdocument, pdfminer.pdftypes

from pdfextract import pdfindexer, pdfelemtransforms, votesearch, dataprovider, ltjson

def get_pdf_num_pages(pdfdata_io: io.BytesIO):
  parser = pdfminer.pdfparser.PDFParser(pdfdata_io)
  document = pdfminer.pdfdocument.PDFDocument(parser)
  num_pages = pdfminer.pdftypes.resolve1(document.catalog["Pages"])["Count"]
  return num_pages

def read_symbols_from_json():
  dirpath = "./"
  with open(os.path.join(dirpath, "symbols_michael_smith.json"), "r", encoding="utf-8") as f:
    json_string = f.read()
  symbols_dicts = json.loads(json_string)
  symbols: typing.Dict[str, typing.List[ltjson.LTJson]] = dict()
  for key, serialized_elems in symbols_dicts.items():
    elems: typing.List[ltjson.LTJson] = []
    for serialized_json in serialized_elems:
      elems.append(ltjson.LTJson(serialized_json=serialized_json))
    symbols[key] = elems
  return symbols

class PdfProcessor:
  def __init__(self,
    pages_gen: typing.Iterator[pdfminer.layout.LTPage],
    data_provider: dataprovider.DataProvider
  ) -> None:
    self.pages_gen = pages_gen
    self.data_provider = data_provider
    self.searcher = votesearch.PdfSearcher()
    self.processing_time = 0.

  def process_page(self):
    for page_number, page in enumerate(self.pages_gen):
      t0 = time.time()
      width = page.width
      height = page.height
      elems = pdfelemtransforms.get_underlying_parent_links(elems=page)
      indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)

      self.searcher.process_page(page_number=page_number, elems=elems, indexer=indexer)
      self.searcher.refine()
      t1 = time.time()
      self.processing_time += t1 - t0
      yield

  def get_results(self):
    return self.searcher.get_results()

def process_pdf(
  data_provider: dataprovider.DataProvider,
  pdfkey:str,
  pdfdata: bytes,
  page_numbers: typing.Union[None, typing.List[int]] = None
):
  pdfdata_io = io.BytesIO(initial_bytes=pdfdata)
  num_pages = get_pdf_num_pages(pdfdata_io=pdfdata_io)
  num_steps_total = num_pages + 1
  data_provider.write_processpdf_start(pdfkey=pdfkey, num_steps_total=num_steps_total)
  pages_gen = pdfminer.high_level.extract_pages(pdf_file=pdfdata_io, page_numbers=page_numbers)
  processor = PdfProcessor(pages_gen=pages_gen, data_provider=data_provider)
  t0 = time.time()
  t_writing = 0.
  for idx, _ in enumerate(processor.process_page()):
    td0 = time.time()
    data_provider.write_processpdf_progress(
      pdfkey=pdfkey,
      curr_step=idx+1,
      message="Processing page: {0}".format(idx+1)
    )
    td1 = time.time()
    t_writing += td1 - td0
  t1 = time.time()
  print(
    "loop took:", t1-t0,
    "elem processing took:", processor.processing_time,
    "Writing progress took:", t_writing
  )
  results = processor.get_results()
  return results
