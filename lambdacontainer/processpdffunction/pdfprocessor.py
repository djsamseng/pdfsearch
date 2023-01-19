
import io
import typing

import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils
import pdfminer.pdfparser, pdfminer.pdfdocument, pdfminer.pdftypes

import dataprovider
import debugutils
from pdfextract import pdfindexer, pdfelemtransforms, votesearch, michaelsmithsymbols

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
    search_rules: typing.List[votesearch.SearchRule] = [
      votesearch.MultiClassSearchRule(shape_matches=[
        symbols["window_label"][0],
      ], description="windows", regex="(?P<class_name>[a-zA-Z])(?P<elem_type>\\d\\d)"),
      votesearch.MultiClassSearchRule(shape_matches=[
        symbols["door_label"][0],
      ], description="doors", regex="(?P<class_name>\\d)(?P<elem_type>\\d\\d)")
    ]
    self.vote_searcher = votesearch.VoteSearcher(search_rules=search_rules)

  def process_page(self):
    for page_number, page in enumerate(self.pages_gen):
      width = page.width
      height = page.height
      elems = pdfelemtransforms.get_underlying_parent_links(elems=page)
      indexer = pdfindexer.PdfIndexer(wrappers=elems, page_width=width, page_height=height)

      self.vote_searcher.process(page_number=page_number, elems=elems, indexer=indexer)
      self.vote_searcher.refine()

      yield

  def get_results(self):
    return self.vote_searcher.get_results()

def process_pdf(data_provider: dataprovider.SupabaseDataProvider, pdfkey:str, pdfdata: bytes):
  pdfdata_io = io.BytesIO(initial_bytes=pdfdata)
  num_pages = get_pdf_num_pages(pdfdata_io=pdfdata_io)
  num_steps_total = num_pages + 1
  data_provider.write_processpdf_start(pdfkey=pdfkey, num_steps_total=num_steps_total)

  pages_gen = pdfminer.high_level.extract_pages(pdf_file=pdfdata_io)
  processor = PdfProcessor(pages_gen=pages_gen, data_provider=data_provider)
  for idx, _ in enumerate(processor.process_page()):
    data_provider.write_processpdf_progress(
      pdfkey=pdfkey,
      curr_step=idx+1,
      message="Processing page: {0}".format(idx+1)
    )
  results = processor.get_results()
  return results
