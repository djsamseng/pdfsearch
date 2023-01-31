
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
  results_json = ""
  if pdfdata is None:
    success = False
    data_provider.write_processpdf_error(
      pdfkey=pdfId,
      error_message="Could not get pdf file for key: {0}".format(pdfId)
    )
  else:
    results = pdfprocessor.process_pdf(data_provider=data_provider, pdfkey=pdfId, pdfdata=pdfdata)
    encoder = ltjson.LTJsonEncoder()
    results_json = encoder.encode(results)
    data_provider.write_pdf_summary(results_json=results_json)
  data_provider.write_processpdf_done(pdfkey=pdfId, success=success)

  return results_json


def handler(
  event: typing.Any,
  context: typing.Any, # pylint:disable=unused-argument
) -> typing.Union[None, str]:
  pdfId = None
  if "pdfId" in event:
    pdfId = event["pdfId"]
  if "body" in event:
    body = event["body"]
    try:
      body_json = json.loads(body)
      if "pdfId" in body_json:
        pdfId = body_json["pdfId"]
    except Exception as e:
      print("Failed to json parse body:", body, e)

  if pdfId is not None:
    print("Found pdfId:", pdfId)
    results_json = process_pdf(pdfId=pdfId)

    if debugutils.is_dev():
      return results_json
  else:
    print("pdfId not in event", event)
  return None
