
import argparse
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


def create_pdf_summary_table():
  resp = db_client.create_table(
    AttributeDefinitions=[
      {
        "AttributeName": "pdf_id",
        "AttributeType": "S",
      },
    ],
    TableName="pdf_summary", # Free tier users
    KeySchema=[
      {
        "AttributeName": "pdf_id",
        "KeyType": "HASH"
      },
    ],
    BillingMode="PROVISIONED", # Required for free tier
    ProvisionedThroughput={
      "ReadCapacityUnits": 10, # 25 free tier total for all tables. 1 = 1 read per second per 4KB item size. 400KB max item size
      "WriteCapacityUnits": 10, # 25 free tier total for all tables
    },
    StreamSpecification={
      "StreamEnabled": False
    },
  )
  print("pdf_summary table:", resp)

def create_pdf_element_locations_table():
  resp = db_client.create_table(
    AttributeDefinitions=[
      {
        "AttributeName": "pdf_id",
        "AttributeType": "S",
      },
    ],
    TableName="pdf_element_locations", # Paid tier users
    KeySchema=[
      {
        "AttributeName": "pdf_id",
        "KeyType": "HASH"
      },
    ],
    BillingMode="PROVISIONED", # Required for free tier
    ProvisionedThroughput={
      "ReadCapacityUnits": 10, # 25 free tier total for all tables. 1 = 1 read per second per 4KB item size. 400KB max item size
      "WriteCapacityUnits": 10, # 25 free tier total for all tables
    },
    StreamSpecification={
      "StreamEnabled": False
    },
  )
  print("pdf_element_locations table:", resp)

def create_streaming_progress_table():
  resp = db_client.create_table(
    AttributeDefinitions=[
      {
        "AttributeName": "pdf_id",
        "AttributeType": "S",
      },
    ],
    TableName="streaming_progress", # Paid tier users
    KeySchema=[
      {
        "AttributeName": "pdf_id",
        "KeyType": "HASH"
      },
    ],
    BillingMode="PROVISIONED", # Required for free tier
    ProvisionedThroughput={
      "ReadCapacityUnits": 2, # 25 free tier total for all tables. 1 = 1 read per second per 4KB item size. 400KB max item size
      "WriteCapacityUnits": 2, # 25 free tier total for all tables
    },
    StreamSpecification={
      "StreamEnabled": True,
      "StreamViewType": "NEW_IMAGE",
    },
  )
  print("streaming_progress table:", resp)

def create_tables():
  # 1. Get the overall information
  # 2. Get the drill in information
  create_pdf_summary_table()
  create_pdf_element_locations_table()
  create_streaming_progress_table()

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

def list_tables():
  tables = db_client.list_tables()
  print(tables)

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--createtables", dest="createtables", default=False, action="store_true")
  parser.add_argument("--listtables", dest="listtables", default=False, action="store_true")
  return parser.parse_args()

def main():
  # DEV_LOCAL=True AWS_ACCESS_KEY_ID="DUMMY" AWS_SECRET_ACCESS_KEY="DUMMY" AWS_DEFAULT_REGION="DUMMY" python3 dataprovider.py --listtables
  # DEV_LOCAL=True python3 dataprovider.py --listtables
  args = parse_args()
  if args.listtables:
    list_tables()
  elif args.createtables:
    create_tables()

if __name__ == "__main__":
  if debugutils.is_dev():
    db_client: typing.Any = boto3.client("dynamodb", endpoint_url="http://localhost:8000") # type: ignore
    main()
  else:
    print("Append DEV_LOCAL=True python3 dataprovider.py")