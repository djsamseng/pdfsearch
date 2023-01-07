
import typing

import boto3
import pdfminer, pdfminer.layout, pdfminer.high_level, pdfminer.utils
import rtree
import scipy

# Remove endpoint_url for production
client = boto3.client("dynamodb", endpoint_url="http://dynamodb-local:8000")

def get_pdf_from_key(pdfkey: str):
  data = client.get_item(
    TableName="pdfstorage",
    Key={
      "id": {
        "S": pdfkey, # String key https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.get_item
      }
    }
  )
  print("Here!", data)
  return data

def process_pdf(pdfkey: str):
  pdfdata = get_pdf_from_key(pdfkey=pdfkey)
  if pdfkey == "plan.pdf":
    pages = pdfminer.high_level.extract_pages(pdf_file=pdfkey, page_numbers=[0])
    for page in pages:
      print(page)

def handler(event: typing.Any, context: typing.Any):
  print(event, context)
  pdfkey = event["pdfkey"]
  print("pdfkey:", pdfkey)
  process_pdf(pdfkey=pdfkey)
  return "Hello from AWS Lambda using Python !!!" + str(event)
