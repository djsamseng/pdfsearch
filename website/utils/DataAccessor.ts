
import SupabaseClient from "@supabase/auth-helpers-react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import useSWR, { mutate, } from "swr";

import { Database } from "./database.types";
import { DatabaseTableNames } from "./tablenames.types";


type PdfSummary = Database["public"]["Tables"]["pdf_summary"]["Row"]
type PdfProcessingProgress = Database["public"]["Tables"]["pdf_processing_progress"]["Row"]

enum SWRKeys {
  GET_PDF_SUMMARY_LIST = "GET_ALL_PDF_SUMMARY_LIST"
}

export class DataAccessor {
  private static _instance: DataAccessor;
  private constructor() {
  }

  public static get instance() {
    if (!this._instance) {
      this._instance = new this();
    }
    return this._instance;
  }

  public async getPdfSummaryIfProcessed({
    supabase,
    pdfId,
  }: {
    supabase: SupabaseClient.SupabaseClient<Database>,
    pdfId: string,
  }) {
    const { data, error, status } = await supabase
      .from(DatabaseTableNames.PDF_SUMMARY)
      .select()
      .eq("pdf_id", pdfId)
      .single();
    if (error && status !== 406) {
      console.error("Failed to check if pdf already processed:", error, status);
      return false;
    }
    if (data && data.pdf_summary !== null) {
      console.log("pdf summary not null:", data);
      return data;
    }
    console.log("406 error no rows - already processed", error);
    return false;
  }

  public async getPdfSummaryList({
    supabase,
  }: {
    supabase: SupabaseClient.SupabaseClient<Database>;
  }) {
    const getPdfSummaryListFetcher = async (supabase: SupabaseClient.SupabaseClient<Database>) => {
      const { data, error, status } = await supabase
          .from(DatabaseTableNames.PDF_SUMMARY)
          .select()
          .not("pdf_summary", "is", "null");
        if (error && status !== 406) {
          console.error("Failed to getAllPdfSummary", error, status);
          return [];
        }
        if (data && data.length > 0) {
          console.log("num pdf summary not null:", data.length);
          return data;
        }
        console.log("getAllPdfSummary no results", error);
        return [];
    }
    const { data, error, } = useSWR(
      SWRKeys.GET_PDF_SUMMARY_LIST,
      () => getPdfSummaryListFetcher(supabase),
      {
        revalidateOnFocus: false,
        revalidateOnReconnect: false,
      });
    if (error) {
      throw error;
    }
    if (!data) {
      throw new Error("No data from getPdfSummaryList")
    }
    return data;
  }
  public mutateAllPdfSummary() {
    mutate(SWRKeys.GET_PDF_SUMMARY_LIST);
  }

  public async insertPdfName({
    supabase,
    pdfId,
    pdfName,
  }: {
    supabase: SupabaseClient.SupabaseClient<Database>;
    pdfId: string;
    pdfName: string;
  }) {
    const { error: insertError } = await supabase
      .from(DatabaseTableNames.PDF_SUMMARY)
      .upsert({
        pdf_id: pdfId,
        pdf_name: pdfName,
      })
    if (insertError) {
      console.error("Failed to insert pdf_summary", insertError);
    }
    console.log("Uploaded pdf");
    return true;
  }

  public async createPdfProccessing({
    supabase,
    pdfId,
  }: {
    supabase: SupabaseClient.SupabaseClient<Database>;
    pdfId: string;
  }) {
    const { error: insertError } = await supabase
      .from(DatabaseTableNames.PDF_PROCESSING_PROGRESS)
      .upsert({
        pdf_id: pdfId,
        total_steps: 1,
        curr_step: 0,
        success: null,
      })
    if (insertError) {
      console.error("Failed to write to pdf_processing_progress", insertError);
    }
  }
}
