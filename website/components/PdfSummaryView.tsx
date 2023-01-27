

import { useState } from "react";
import { Database } from "../utils/database.types";

import PdfView from "./PdfView";
import { CompletePdfSummary } from "../utils/requestresponsetypes";
import SummaryElementList from "./SummaryElementList";

enum PdfSummaryMode {
  SUMMARY = "SUMMARY",
  SPLIT = "SPLIT",
  PDF = "PDF",
}

export default function PdfSummaryView({
  pdfSummary,
}: {
  pdfSummary: CompletePdfSummary;
}) {

  const [ summaryViewMode, setSummaryViewMode ] = useState(PdfSummaryMode.SPLIT);

  // https://flowbite.com/docs/getting-started/introduction/
  const sharedButtonStyle = "px-4 py-2 border-blue-600 hover:ring-2";
  const selectedStyle = "bg-blue-600 text-white";
  const unselectedStyle = "text-blue-600 ";

  const summaryButtonStyle = `${sharedButtonStyle} ${summaryViewMode === PdfSummaryMode.SUMMARY ? selectedStyle : unselectedStyle} border rounded-l-lg`;
  const splitModeButtonStyle = `${sharedButtonStyle} ${summaryViewMode === PdfSummaryMode.SPLIT ? selectedStyle : unselectedStyle} border-y border-r`;
  const viewPdfButtonStyle = `${sharedButtonStyle} ${summaryViewMode === PdfSummaryMode.PDF ? selectedStyle : unselectedStyle} border-y border-r rounded-r-lg`;
  return (
    <div className="flex flex-col items-center">
      <div className="grid grid-cols-3 rounded-md text-sm shadow-sm" role="group">
        <button type="button"
          className={summaryButtonStyle}
          onClick={() => setSummaryViewMode(PdfSummaryMode.SUMMARY)}>
          Summary
        </button>
        <button type="button"
          className={splitModeButtonStyle}
          onClick={() => setSummaryViewMode(PdfSummaryMode.SPLIT)}>
          Split
        </button>
        <button type="button"
          className={viewPdfButtonStyle}
          onClick={() => setSummaryViewMode(PdfSummaryMode.PDF)}>
          View PDF
        </button>
      </div>
      <div className="w-full">
        { summaryViewMode === PdfSummaryMode.SUMMARY && (
          <SummaryElementList pdfSummary={pdfSummary} />
        )}
        { summaryViewMode === PdfSummaryMode.SPLIT && (
          <div className="grid grid-cols-2 gap-4">
            <SummaryElementList pdfSummary={pdfSummary} />
            <PdfView pdfSummary={pdfSummary} smallCanvas={true} />
          </div>
        )}
        { summaryViewMode === PdfSummaryMode.PDF && (
          <PdfView pdfSummary={pdfSummary} smallCanvas={false} />
        )}
      </div>

    </div>
  )
}