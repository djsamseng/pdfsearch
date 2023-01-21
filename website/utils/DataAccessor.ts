
import SupabaseClient from "@supabase/auth-helpers-react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";
import { supabase } from "@supabase/auth-ui-react/dist/esm/common/theming";

import useSWR, { mutate, } from "swr";

import { Database } from "./database.types";
import { DatabaseTableNames } from "./tablenames.types";
import { CompletePdfSummary } from "./requestresponsetypes";

export enum SWRKeys {
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
      console.log("pdf_summary not null:", data);
      return data;
    }
    console.log("pdf_summary resp:", !!data, "pdf_summary json:", data && !!data.pdf_summary);
    return false;
  }

  public async getPdfSummaryList({
    supabase,
  }: {
    supabase: SupabaseClient.SupabaseClient<Database>;
  }) {
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
      const completeSummary: CompletePdfSummary[] = data
        .filter(elem => {
          return typeof elem.pdf_summary === "string";
        })
        .map(elem => {
          return {
            pdfId: elem.pdf_id,
            pdfName: elem.pdf_name,
            pdfSummary: JSON.parse(elem.pdf_summary as string),
          }
        })
      return completeSummary;
    }
    console.log("getAllPdfSummary no results", error);
    return [];
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

  public async getPdfProcessingProgress({
    supabase,
    pdfId,
  }: {
    supabase: SupabaseClient.SupabaseClient<Database>;
    pdfId: string;
  }) {
    const { data, error } = await supabase
      .from(DatabaseTableNames.PDF_PROCESSING_PROGRESS)
      .select()
      .eq("pdf_id", pdfId)
      .single();
    if (error) {
      console.error("Failed to get pdf processing progress:", error);
    }
    return data;
  }

  public async getPdfBytes({
    supabase,
    pdfId,
  }: {
    supabase: SupabaseClient.SupabaseClient<Database>;
    pdfId: string;
  }) {
    const url = `public/${pdfId}.pdf`;
    console.log("Getting pdf:", url);
    const { data, error } = await supabase.storage
      .from("pdfs")
      .download(url);
    if (error) {
      console.error("Failed to getPdfBytes:", error);
      throw(error);
    }
    if (!data) {
      throw new Error("Test");
    }
    return data.arrayBuffer();
  }
}
