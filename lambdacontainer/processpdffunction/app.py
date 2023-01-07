
import typing

import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils
import rtree
import scipy


def process_pdf(pdfkey: str):
  if pdfkey == "plan.pdf":
    pages = pdfminer.high_level.extract_pages(pdf_file=pdfkey, page_numbers=[0])
    for page in pages:
      print(page)

def handler(event: typing.Any, context: typing.Any):
  print(event, context)
  pdfkey = event["pdfkey"]
  process_pdf(pdfkey=pdfkey)
  return "Hello from AWS Lambda using Python !!!" + str(event)
