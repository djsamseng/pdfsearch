
import SupabaseClient from "@supabase/auth-helpers-react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import Link from "next/link";
import { useEffect, useState } from "react";
import useSWR from "swr";

import { Database } from "../utils/database.types";
import { DataAccessor } from "../utils/DataAccessor";
import { DatabaseTableNames } from "../utils/tablenames.types";

type PdfSummary = Database["public"]["Tables"]["pdf_summary"]["Row"]

export default function MyPdfsView() {
  const supabase = useSupabaseClient<Database>();
  const [ pdfSummaryList, setPdfSummaryList ] = useState<PdfSummary[]>([]);
  useEffect(() => {
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
    getPdfSummaryListFetcher(supabase)
    /*DataAccessor.instance.getPdfSummaryList({
      supabase,
    })*/
    .then(data => {
      setPdfSummaryList(data);
    })
    .catch(error => {
      console.error("Failed to getPdfSummaryList:", error);
    });
  }, []);
  const myPdfList = pdfSummaryList.map(pdfSummary => {
    const summaryJson = JSON.parse(pdfSummary.pdf_summary as string);
    const houseName = "houseName" in summaryJson ? summaryJson["houseName"] as string : "";
    const architectName = "architectName" in summaryJson ? summaryJson["architectName"] as string : "";
    return {
      pdfId: pdfSummary.pdf_id,
      pdfName: pdfSummary.pdf_name,
      houseName,
      architectName,
      numPages: 0,
    }
  });
  const pdfLinks = myPdfList.map((myPdf, idx) => {
    return (
      <li className="border-x border-gray border-t first:rounded-t-xl last:border-b last:rounded-b-xl pl-2 hover:bg-gray-200"
        key={myPdf.pdfId}>
        <Link href={`/viewer/${myPdf.pdfId}?pdfname=${myPdf.pdfName}`} className="">
          <div className="grid grid-cols-3 gap-4 place-content-stretch">
            <span className="p-2">{ myPdf.pdfName }</span>
            <span className="p-2">{ myPdf.houseName }</span>
            <span className="p-2">{ myPdf.architectName }</span>
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
