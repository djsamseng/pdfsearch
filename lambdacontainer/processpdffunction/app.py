
import typing

import dataprovider
import pdfprocessor

def process_pdf(pdfkey: str):
  pdfdata = dataprovider.get_pdf_for_key(pdfkey=pdfkey)
  success = True
  if pdfdata is None:
    success = False
    dataprovider.write_processpdf_error(pdfkey=pdfkey, error_message="Could not get pdf file for key: {0}".format(pdfkey))
  else:
    pdfprocessor.process_pdf(pdfkey=pdfkey, pdfdata=pdfdata)
  dataprovider.write_processpdf_done(pdfkey=pdfkey, success=success)


def handler(event: typing.Any, context: typing.Any):
  pdfkey = event["pdfkey"]
  process_pdf(pdfkey=pdfkey)
  return "Hello from AWS Lambda using Python !!!" + str(event)
