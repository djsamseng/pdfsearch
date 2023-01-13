
import json
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
  pdfId = event["pdfId"]
  process_pdf(pdfkey=pdfId)
  ret: typing.Dict[str, typing.Any] = {
    'statusCode': 200,
    'headers': {
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Origin': 'http://localhost:3000',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    },
    'body': json.dumps('Hello from Lambda!')
  }
  print("Returning:", ret)
  return ret
