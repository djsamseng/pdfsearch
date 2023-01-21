
import SupabaseClient from "@supabase/auth-helpers-react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import Link from "next/link";
import { useEffect, useState } from "react";
import useSWR from "swr";

import { Database } from "../utils/database.types";
import { DataAccessor, SWRKeys } from "../utils/DataAccessor";
import { DatabaseTableNames } from "../utils/tablenames.types";

type PdfSummaryTable = Database["public"]["Tables"]["pdf_summary"]["Row"]

export default function MyPdfsView() {
  const supabase = useSupabaseClient<Database>();
  const { data, error, isLoading } = useSWR(
    SWRKeys.GET_PDF_SUMMARY_LIST,
    () => DataAccessor.instance.getPdfSummaryList({ supabase }),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    });
  const pdfSummaryList = data ? data : [];
  const myPdfList = data || [];
  const pdfLinks = myPdfList.map((myPdf, idx) => {
    return (
      <li className="border-x border-gray border-t first:rounded-t-xl last:border-b last:rounded-b-xl pl-2 hover:bg-gray-200"
        key={myPdf.pdfId}>
        <Link href={`/viewer/${myPdf.pdfId}?pdfname=${myPdf.pdfName}`} className="">
          <div className="grid grid-cols-3 gap-4 place-content-stretch">
            <span className="p-2">{ myPdf.pdfName }</span>
            <span className="p-2">{ myPdf.pdfSummary.houseName }</span>
            <span className="p-2">{ "Architect" }</span>
          </div>
        </Link>
      </li>
    )
  });
  return (
    <div className="w-1/2 min-w-fit mx-auto">
      <div className="text-center mt-5 text-xl">
        My PDFs
      </div>
      <div>
        <div className="grid grid-cols-3 gap-4 place-content-stretch mt-2">
            <span className="pl-4">PDF</span>
            <span className="pl-4">House</span>
            <span className="pl-4">Architect</span>
          </div>
        <ul role="listbox" className="w-full">
          { pdfLinks }
        </ul>
      </div>

    </div>
  );
}
