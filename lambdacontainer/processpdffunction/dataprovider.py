
import abc
import argparse
import enum
import os
import typing

import supabase
import storage3 # type: ignore
import debugutils

supabase_url = os.environ.get("SUPABASE_URL") or ""
supabase_key = os.environ.get("SUPABASE_KEY") or ""
print("Supabase url:", supabase_url, "Key:", supabase_key)
db_client: supabase.client.Client = supabase.client.create_client(
  supabase_url=supabase_url,
  supabase_key=supabase_key
)

# Match /website/utils/tablenames.types.ts
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

class PdfSummaryTable(enum.Enum):
  PDF_ID = "pdf_id"
  PDF_SUMMARY = "pdf_summary"
  PDF_NAME = "pdf_name"

UpdateType = typing.Dict[str, typing.Dict[str, typing.Dict[str, typing.Union[str, int, bool]]]]
KeyType = typing.Dict[str, typing.Dict[str, typing.Union[str, int, bool]]]

class DataProvider(metaclass=abc.ABCMeta):
  @abc.abstractmethod
  def get_pdf_for_key(self, pdfkey: str) -> typing.Union[None, bytes]:
    pass

  @abc.abstractmethod
  def write_processpdf_start(self, pdfkey: str, num_steps_total: int):
    pass

  @abc.abstractmethod
  def write_processpdf_progress(self, pdfkey: str, curr_step: int, message: str):
    pass

  @abc.abstractmethod
  def write_processpdf_error(self, pdfkey: str, error_message: str):
    pass

  @abc.abstractmethod
  def write_processpdf_done(self, pdfkey: str, success: bool):
    pass

class SupabaseDataProvider(DataProvider):
  def __init__(self, pdfId: str) -> None:
    self.pdfId = pdfId

  def get_pdf_for_key(self, pdfkey: str) -> typing.Union[None, bytes]:
    if debugutils.is_dev():
      if os.path.exists(pdfkey):
        with open(file=pdfkey, mode="rb") as f:
          binary_str = f.read()
          return binary_str
    try:
      storage_client: storage3.SyncStorageClient = typing.cast(
        storage3.SyncStorageClient,
        db_client.storage()
      )
      pdf_bytes = storage_client.from_("pdfs").download("public/" + pdfkey + ".pdf")
      return pdf_bytes
    except Exception as e:
      print("PDF: {0} not found", pdfkey, e)
    return None

  def write_pdf_summary(self, results_json: str):
    data = {
      PdfSummaryTable.PDF_ID.value: self.pdfId,
      PdfSummaryTable.PDF_SUMMARY.value: results_json,
    }
    try:
      db_client.table(TableNames.PDF_SUMMARY.value)\
        .update(json=data).eq(PdfSummaryTable.PDF_ID.value, self.pdfId).execute() # type: ignore
    except Exception as e:
      print("Failed to write_pdf_summary:", e)

  def write_processpdf_start(self, pdfkey: str, num_steps_total: int):
    data = {
      StreamingProgressTable.PDF_ID.value: pdfkey,
      StreamingProgressTable.TOTAL_STEPS.value: num_steps_total,
    }
    try:
      db_client.table(TableNames.STREAMING_PROGRESS.value)\
        .update(json=data).eq(StreamingProgressTable.PDF_ID.value, pdfkey).execute() # type:ignore
    except Exception as e:
      print("Failed to write_processpdf_start:", e)

  def write_processpdf_progress(self, pdfkey: str, curr_step: int, message: str):
    data = {
      StreamingProgressTable.PDF_ID.value: pdfkey,
      StreamingProgressTable.CURR_STEP.value: curr_step,
      StreamingProgressTable.MSG.value: message
    }
    try:
      db_client.table(TableNames.STREAMING_PROGRESS.value)\
        .update(json=data).eq(StreamingProgressTable.PDF_ID.value, pdfkey).execute() # type:ignore
    except Exception as e:
      print("Failed to write_processpdf_progress:", e)

  def write_processpdf_error(self, pdfkey: str, error_message: str):
    # Could occur before start
    data = {
      StreamingProgressTable.PDF_ID.value: pdfkey,
      StreamingProgressTable.MSG.value: error_message
    }
    try:
      db_client.table(TableNames.STREAMING_PROGRESS.value)\
        .update(json=data).eq(StreamingProgressTable.PDF_ID.value, pdfkey).execute() # type:ignore
    except Exception as e:
      print("Failed to write_processpdf_error:", e)

  def write_processpdf_done(self, pdfkey: str, success: bool):
    data = {
      StreamingProgressTable.PDF_ID.value: pdfkey,
      StreamingProgressTable.SUCCESS.value: success,
    }
    try:
      db_client.table(TableNames.STREAMING_PROGRESS.value)\
        .update(json=data).eq(StreamingProgressTable.PDF_ID.value, pdfkey).execute() # type:ignore
    except Exception as e:
      print("Failed to write_processpdf_done:", e)

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--listtables", dest="listtables", default=False, action="store_true")
  parser.add_argument("--scanstream", dest="scanstream", default=False, action="store_true")
  return parser.parse_args()
