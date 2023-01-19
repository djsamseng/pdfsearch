
import json
import typing

import dataprovider
import pdfprocessor
import debugutils
from pdfextract import ltjson

def process_pdf(pdfId: str):
  data_provider = dataprovider.SupabaseDataProvider(pdfId=pdfId)
  pdfdata = data_provider.get_pdf_for_key(pdfkey=pdfId)
  success = True
  results: typing.Dict[str, typing.Any] = {}
  if pdfdata is None:
    success = False
    data_provider.write_processpdf_error(
      pdfkey=pdfId,
      error_message="Could not get pdf file for key: {0}".format(pdfId)
    )
  else:
    results = pdfprocessor.process_pdf(data_provider=data_provider, pdfkey=pdfId, pdfdata=pdfdata)
  data_provider.write_processpdf_done(pdfkey=pdfId, success=success)
  return results


def handler(event: typing.Any, context: typing.Any
) -> typing.Union[None, str]:
  pdfId = event["pdfId"]
  results = process_pdf(pdfId=pdfId)
  encoder = ltjson.LTJsonEncoder()
  results_json = encoder.encode(results)
  if debugutils.is_dev():
    return results_json
  return None
