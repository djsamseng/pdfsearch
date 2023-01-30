
import io
import json
import os
import typing
import time

import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils
import pdfminer.pdfparser, pdfminer.pdfdocument, pdfminer.pdftypes

import dataprovider
from pdfextract import pdfindexer, pdfelemtransforms, votesearch, ltjson

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

# Recognizer is the opposite of searching in terms of datastructures
# Recognizer is good for classifying areas
# Recognizer easily misses things
# Searching is good for pulling together what I recognized
# Searching easily finds things that don't count
# 1. Take a quick look and recognize areas
# 2. This gives me a good idea of what to search for on this page and where
class ArchitectRecognizer:
  def __init__(self) -> None:
    pass

class SymbolRecognizer:
  def __init__(self, ) -> None:
    pass

class TableRecognizer:
  def __init__(self) -> None:
    pass

class PageProcessor:
  def __init__(self) -> None:
    self.architect_vote = []

class PdfProcessor:
  def __init__(self,
    pages_gen: typing.Iterator[pdfminer.layout.LTPage],
    data_provider: dataprovider.SupabaseDataProvider
  ) -> None:
    self.pages_gen = pages_gen
    self.data_provider = data_provider
    symbols = read_symbols_from_json()
    self.window_search_rule = votesearch.RegexShapeSearchRule(
      shape_matches=[
        symbols["window_label"][0],
      ],
      description="windows",
      regex="^(?P<class_name>[a-zA-Z])(?P<elem_type>\\d\\d)"
    )
    self.door_search_rule = votesearch.RegexShapeSearchRule(
      shape_matches=[
        symbols["door_label"][0],
      ],
      description="doors",
      regex="^(?P<class_name>\\d)(?P<elem_type>\\d\\d)"
    )
    search_rules: typing.List[votesearch.SearchRule] = [
      self.window_search_rule,
      self.door_search_rule,
      votesearch.HouseNameSearchRule(description="houseName"),
      votesearch.ArchitectNameSearchRule(description="architectName"),
    ]
    page_rules = [
      votesearch.PageNameSearchRule(description="pageNames"),
      votesearch.WindowScheduleSearchRule(window_search_rule=self.window_search_rule),
      votesearch.DoorScheduleSearchRule(door_search_rule=self.door_search_rule),
      votesearch.LightingScheduleSearchRule(),
    ]
    self.vote_searcher = votesearch.VoteSearcher(search_rules=search_rules, page_rules=page_rules)
    self.processing_time = 0.

  def process_page(self):
    for page_number, page in enumerate(self.pages_gen):
      t0 = time.time()
      width = page.width
      height = page.height
      elems = pdfelemtransforms.get_underlying_parent_links(elems=page)
      indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)

      self.vote_searcher.process_page(page_number=page_number, elems=elems, indexer=indexer)
      self.vote_searcher.refine()
      t1 = time.time()
      self.processing_time += t1 - t0
      yield

  def get_results(self):
    return self.vote_searcher.get_results()

def process_pdf(data_provider: dataprovider.SupabaseDataProvider, pdfkey:str, pdfdata: bytes):
  pdfdata_io = io.BytesIO(initial_bytes=pdfdata)
  num_pages = get_pdf_num_pages(pdfdata_io=pdfdata_io)
  num_steps_total = num_pages + 1
  data_provider.write_processpdf_start(pdfkey=pdfkey, num_steps_total=num_steps_total)

  pages_gen = pdfminer.high_level.extract_pages(pdf_file=pdfdata_io) # 2,5,9
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
