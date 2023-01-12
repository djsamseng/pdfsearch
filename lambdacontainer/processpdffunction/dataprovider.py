
import argparse
import enum
import os
import typing

import boto3 # type: ignore
import botocore.exceptions # type: ignore
import supabase
import storage3
import postgrest.types # type: ignore

import debugutils

supabase_url = os.environ.get("SUPABASE_URL") or ""
supabase_key = os.environ.get("SUPABASE_KEY") or ""
db_client: supabase.client.Client = supabase.client.create_client(supabase_url=supabase_url, supabase_key=supabase_key)
if debugutils.is_dev():
  s3_client: typing.Any = None
else:
  s3_client: typing.Any = boto3.resource("s3") # type: ignore

class TableNames(enum.Enum):
  PDF_SUMMARY = "pdf_summary"
  PDF_ELEMENT_LOCATIONS = "pdf_element_locations"
  STREAMING_PROGRESS = "pdf_processing_progress"

class StreamingProgressTable(enum.Enum):
  PDF_ID = "pdf_id"
  TOTAL_STEPS = "total_steps"
  CURR_STEP = "curr_step"
  MSG = "msg"
  SUCCESS = "success"

def get_pdf_for_key(pdfkey: str) -> typing.Union[None, bytes]:
  if s3_client is None:
    if os.path.exists(pdfkey):
      with open(file=pdfkey, mode="rb") as f:
        binary_str = f.read()
        return binary_str
    try:
      storage_client: storage3.SyncStorageClient = typing.cast(storage3.SyncStorageClient, db_client.storage)
      bytes = storage_client.from_("pdfs").download(pdfkey)
      print("got bytes:", bytes)
      return bytes
    except Exception as e:
      print("DEV_LOCAL: {0} not found", pdfkey, e)
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


def write_processpdf_start(pdfkey: str, num_steps_total: int):
  data = {
    StreamingProgressTable.PDF_ID.value: pdfkey,
    StreamingProgressTable.TOTAL_STEPS.value: num_steps_total,
  }
  db_client.table(TableNames.STREAMING_PROGRESS.value).update(json=data).eq(StreamingProgressTable.PDF_ID.value, pdfkey).execute() # type:ignore

def write_processpdf_progress(pdfkey: str, curr_step: int, message: str):
  data = {
    StreamingProgressTable.PDF_ID.value: pdfkey,
    StreamingProgressTable.CURR_STEP.value: curr_step,
    StreamingProgressTable.MSG.value: message
  }
  db_client.table(TableNames.STREAMING_PROGRESS.value).update(json=data).eq(StreamingProgressTable.PDF_ID.value, pdfkey).execute() # type:ignore

def write_processpdf_error(pdfkey: str, error_message: str):
  # Could occur before start
  data = {
    StreamingProgressTable.PDF_ID.value: pdfkey,
    StreamingProgressTable.MSG.value: error_message
  }
  db_client.table(TableNames.STREAMING_PROGRESS.value).update(json=data).eq(StreamingProgressTable.PDF_ID.value, pdfkey).execute() # type:ignore

def write_processpdf_done(pdfkey: str, success: bool):
  data = {
    StreamingProgressTable.PDF_ID.value: pdfkey,
    StreamingProgressTable.SUCCESS.value: success,
  }
  db_client.table(TableNames.STREAMING_PROGRESS.value).update(json=data).eq(StreamingProgressTable.PDF_ID.value, pdfkey).execute() # type:ignore

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--listtables", dest="listtables", default=False, action="store_true")
  parser.add_argument("--scanstream", dest="scanstream", default=False, action="store_true")
  return parser.parse_args()

def main():
  # DEV_LOCAL=True python3 dataprovider.py
  # args = parse_args()
  return

if __name__ == "__main__":
  if debugutils.is_dev():
    main()
  else:
    print("Append DEV_LOCAL=True python3 dataprovider.py")