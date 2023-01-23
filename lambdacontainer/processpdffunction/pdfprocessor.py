
import io
import typing
import time

import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils
import pdfminer.pdfparser, pdfminer.pdfdocument, pdfminer.pdftypes

import dataprovider
import debugutils
from pdfextract import pdfindexer, pdfelemtransforms, votesearch, michaelsmithsymbols, ltjson

def get_pdf_num_pages(pdfdata_io: io.BytesIO):
  parser = pdfminer.pdfparser.PDFParser(pdfdata_io)
  document = pdfminer.pdfdocument.PDFDocument(parser)
  num_pages = pdfminer.pdftypes.resolve1(document.catalog["Pages"])["Count"]
  return num_pages

def read_symbols_from_json():
  return michaelsmithsymbols.read_symbols_from_json(dirpath="./")

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
    def window_search_rule_add_match_to_results(
      results: votesearch.MultiClassSearchRuleResults,
      page_number: int,
      class_name: str,
      elem_type: str,
      elem: ltjson.LTJsonResponse
    ):
      # TODO: comes from door schedule
      full_id = class_name + elem_type
      display_class_name = class_name + "##"
      results[page_number][display_class_name][full_id].append(elem)
    self.window_search_rule.add_match_to_results = window_search_rule_add_match_to_results
    self.door_search_rule = votesearch.RegexShapeSearchRule(
      shape_matches=[
        symbols["door_label"][0],
      ],
      description="doors",
      regex="^(?P<class_name>\\d)(?P<elem_type>\\d\\d)"
    )
    def door_search_rule_add_match_to_results(
      results: votesearch.MultiClassSearchRuleResults,
      page_number: int,
      class_name: str,
      elem_type: str,
      elem: ltjson.LTJsonResponse
    ):
      # TODO: Comes from window schedule
      full_id = class_name + elem_type
      display_class_name = "A"
      id_to_class_name = {
        "101": "B",
        "102": "B",
        "103": "A",
        "201": "A",
        "202": "A",
        "203": "A",
        "204": "C",
        "205": "C"
      }
      if full_id in id_to_class_name:
        display_class_name = id_to_class_name[full_id]
      results[page_number][display_class_name][full_id].append(elem)
    self.door_search_rule.add_match_to_results = door_search_rule_add_match_to_results
    search_rules: typing.List[votesearch.SearchRule] = [
      self.window_search_rule,
      self.door_search_rule,
      votesearch.HouseNameSearchRule(description="houseName"),
      votesearch.ArchitectNameSearchRule(description="architectName"),

    ]
    page_rules = [
      votesearch.PageNameSearchRule(description="pageNames")
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

  if debugutils.is_dev() and False:
    pages_gen = pdfminer.high_level.extract_pages(pdf_file=pdfdata_io, page_numbers=[9])
  else:
    pages_gen = pdfminer.high_level.extract_pages(pdf_file=pdfdata_io)
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
