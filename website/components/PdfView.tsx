
import React, { useRef, useState, MouseEvent, useEffect } from "react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";
import * as PdfJS  from "pdfjs-dist/build/pdf"
import useSWR from "swr";

import { DataAccessor } from "../utils/DataAccessor";
import { usePdf } from "../utils/UsePdf";
import { Database } from "../utils/database.types";
import { CompletePdfSummary } from "../utils/requestresponsetypes";
import { PdfImageView } from "./PdfImageView";
import { LoadingSpinner } from "./LoadingSpinner";


export default function PdfView({
  pdfSummary,
  smallCanvas,
}: {
  pdfSummary: CompletePdfSummary;
  smallCanvas: boolean;
}) {
  const supabase = useSupabaseClient<Database>();
  const { data: pdfData, error, isLoading } = useSWR(
    `storage/${pdfSummary.pdfId}.pdf`,
    () => DataAccessor.instance.getPdfBytes({
      supabase,
      pdfId: pdfSummary.pdfId,
    }),
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  )
  if (pdfData) {
    return (
      <PdfImageView pdfData={pdfData} />
    );
  }
  else if (isLoading) {
    return (
      <div className="my-4">
        <LoadingSpinner text={`Downloading ${pdfSummary.pdfName}`} />
      </div>
    );
  }
  else {
    return (
      <div className="my-4 text-center space-y-2">
        <div>
          <span>An error occurred downloading the pdf</span>
        </div>
        <div>
          <span>{ pdfSummary.pdfName }</span>
        </div>
        <div>
          <span>{ pdfSummary.pdfId }</span>
        </div>
        <div>
          <span>{ error && JSON.stringify(error, null, 4) }</span>
        </div>
      </div>
    )
  }
}