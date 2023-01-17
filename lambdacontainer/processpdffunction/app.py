
import json
import typing

import dataprovider
import pdfprocessor
import debugutils
from pdfextract import ltjson

def process_pdf(pdfkey: str):
  pdfdata = dataprovider.get_pdf_for_key(pdfkey=pdfkey)
  success = True
  results: typing.Dict[str, typing.Any] = {}
  if pdfdata is None:
    success = False
    dataprovider.write_processpdf_error(
      pdfkey=pdfkey,
      error_message="Could not get pdf file for key: {0}".format(pdfkey)
    )
  else:
    results = pdfprocessor.process_pdf(pdfkey=pdfkey, pdfdata=pdfdata)
  dataprovider.write_processpdf_done(pdfkey=pdfkey, success=success)
  return results


def handler(event: typing.Any, context: typing.Any
) -> typing.Union[None, str]:
  pdfId = event["pdfId"]
  results = process_pdf(pdfkey=pdfId)
  if debugutils.is_dev():
    encoder = ltjson.LTJsonEncoder()
    return encoder.encode(results)
  return None
