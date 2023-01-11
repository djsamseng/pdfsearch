
import argparse
import enum
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

class TableNames(enum.Enum):
  PDF_SUMMARY = "pdf_summary"
  PDF_ELEMENT_LOCATIONS = "pdf_element_locations"
  STREAMING_PROGRESS = "streaming_progress"


def create_pdf_summary_table():
  resp = db_client.create_table(
    AttributeDefinitions=[
      {
        "AttributeName": "pdf_id",
        "AttributeType": "S",
      },
    ],
    TableName=TableNames.PDF_SUMMARY.value, # Free tier users
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
    TableName=TableNames.PDF_ELEMENT_LOCATIONS.value, # Paid tier users
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
    TableName=TableNames.STREAMING_PROGRESS.value, # Paid tier users
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
    print("DEV_LOCAL: {0} not found", pdfkey)
    return None
  try:
    resp = s3_client.get_object(
      Bucket="",
      Key=pdfkey,
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
  return None

UpdateType = typing.Dict[str, typing.Dict[str, typing.Dict[str, typing.Union[str, int, bool]]]]
KeyType = typing.Dict[str, typing.Dict[str, typing.Union[str, int, bool]]]
def make_streaming_progress_item(
  pdfkey: str,
  curr_step: typing.Union[int, None] = None,
  num_steps_total: typing.Union[int, None] = None,
  message: typing.Union[str, None] = None,
  success: typing.Union[bool, None] = None,
) -> typing.Tuple[KeyType, KeyType]:
  key: KeyType = {
    "pdf_id": {
      "S": pdfkey,
    }
  }
  item: KeyType = {}
  if curr_step is not None:
    item["curr_step"] = {
      "N": str(curr_step),
    }
  if num_steps_total is not None:
    item["num_steps_total"] = {
      "N": str(num_steps_total),
    }
  if message is not None:
    item["message"] = {
      "S": message,
    }
  if success is not None:
    item["success"] = {
      "BOOL": success,
    }
  return key, item

def make_streaming_progress_put(
  pdfkey: str,
  curr_step: typing.Union[int, None] = None,
  num_steps_total: typing.Union[int, None] = None,
  message: typing.Union[str, None] = None,
  success: typing.Union[bool, None] = None,
):
  key_obj, content_obj = make_streaming_progress_item(
    pdfkey=pdfkey,
    curr_step=curr_step,
    num_steps_total=num_steps_total,
    message=message,
    success=success)
  for key, val in key_obj.items():
    content_obj[key] = val
  return content_obj

def make_streaming_progress_update(
  pdfkey: str,
  curr_step: typing.Union[int, None] = None,
  num_steps_total: typing.Union[int, None] = None,
  message: typing.Union[str, None] = None,
  success: typing.Union[bool, None] = None,
):
  key_obj, content_obj = make_streaming_progress_item(
    pdfkey=pdfkey,
    curr_step=curr_step,
    num_steps_total=num_steps_total,
    message=message,
    success=success)
  update_obj: UpdateType = {}
  for key, val in content_obj.items():
    update_obj[key] = {
      "Value": val,
    }
  return key_obj, update_obj

def write_processpdf_start(pdfkey: str, num_steps_total: int):
  item = make_streaming_progress_put(pdfkey=pdfkey, curr_step=0, num_steps_total=num_steps_total)
  db_client.put_item(
    TableName=TableNames.STREAMING_PROGRESS.value,
    Item=item
  )

def write_processpdf_progress(pdfkey: str, curr_step: int, message: str):
  key, update = make_streaming_progress_update(pdfkey=pdfkey, curr_step=curr_step)
  db_client.update_item(
    TableName=TableNames.STREAMING_PROGRESS.value,
    Key=key,
    AttributeUpdates=update,
  )

def write_processpdf_error(pdfkey: str, error_message: str):
  # Could occur before start
  key, update = make_streaming_progress_update(pdfkey=pdfkey, message=error_message)
  db_client.update_item(
    TableName=TableNames.STREAMING_PROGRESS.value,
    Key=key,
    AttributeUpdates=update,
  )

def write_processpdf_done(pdfkey: str, success: bool):
  key, update = make_streaming_progress_update(pdfkey=pdfkey, success=success)
  db_client.update_item(
    TableName=TableNames.STREAMING_PROGRESS.value,
    Key=key,
    AttributeUpdates=update,
  )

def get_from_key(pdfkey: str):
  data = db_client.get_item(
    TableName="pdf_summary",
    Key={
      "pdf_id": {
        "S": pdfkey, # String key https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.get_item
      }
    }
  )
  return data

def scan_streaming_progress():
  resp = db_client.scan(
    TableName=TableNames.STREAMING_PROGRESS.value,
    Select="ALL_ATTRIBUTES",
  )
  print(resp)

def list_tables():
  tables = db_client.list_tables()
  print(tables)

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--createtables", dest="createtables", default=False, action="store_true")
  parser.add_argument("--listtables", dest="listtables", default=False, action="store_true")
  parser.add_argument("--scanstream", dest="scanstream", default=False, action="store_true")
  return parser.parse_args()

def main():
  # DEV_LOCAL=True AWS_ACCESS_KEY_ID="DUMMY" AWS_SECRET_ACCESS_KEY="DUMMY" AWS_DEFAULT_REGION="DUMMY" python3 dataprovider.py --listtables
  # DEV_LOCAL=True python3 dataprovider.py --listtables
  args = parse_args()
  if args.listtables:
    list_tables()
  if args.createtables:
    create_tables()
  if args.scanstream:
    scan_streaming_progress()

if __name__ == "__main__":
  if debugutils.is_dev():
    db_client: typing.Any = boto3.client("dynamodb", endpoint_url="http://localhost:8000") # type: ignore
    main()
  else:
    print("Append DEV_LOCAL=True python3 dataprovider.py")