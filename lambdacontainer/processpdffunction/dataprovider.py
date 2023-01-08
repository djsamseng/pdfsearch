
import os
import typing

import boto3 # type: ignore
import botocore.exceptions # type: ignore

import debugutils

if debugutils.is_dev():
  s3_client: typing.Any = None
  db_client: typing.Any = boto3.client("dynamodb", endpoint_url="http://dynamodb-local:8000") # type: ignore
else:
  s3_client: typing.Any = boto3.resource("s3") # type: ignore
  db_client: typing.Any = boto3.client("dynamodb") # type: ignore


def get_pdf_for_key(pdfkey: str) -> typing.Union[None, bytes]:
  if s3_client is None:
    if os.path.exists(pdfkey):
      with open(file=pdfkey, mode="rb") as f:
        binary_str = f.read()
        return binary_str
  try:
    resp = s3_client.get_object(
      Bucket="",
      Key="",
    )
    return resp["Body"].read()
  except botocore.exceptions.NoSuchKey as e: # type: ignore
    e = typing.cast(typing.Any, e)
    print(e)
  except botocore.exceptions.InvalidObjectState as e: # type: ignore
    e = typing.cast(typing.Any, e)
    print(e)
  except Exception as e:
    print(e)

def write_processpdf_start(pdfkey: str, num_steps_total: int):
  print(pdfkey, "start: 0 /", num_steps_total)

def write_processpdf_progress(pdfkey: str, cur_step: int, message: str):
  print(pdfkey, "Step:", cur_step)

def write_processpdf_error(pdfkey: str, error_message: str):
  # Could occur before start
  print(pdfkey, "Error:", error_message)

def write_processpdf_done(pdfkey: str, success: bool):
  print(pdfkey, "Done success:", success)

def get_from_key(pdfkey: str):
  data = db_client.get_item(
    TableName="pdfstorage",
    Key={
      "id": {
        "S": pdfkey, # String key https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.get_item
      }
    }
  )
  print("Here!", data)
  return data