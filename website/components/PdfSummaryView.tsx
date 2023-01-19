

import { useState } from "react";
import { Database } from "../utils/database.types";

import PdfView from "./PdfView";

type PdfSummary = Database["public"]["Tables"]["pdf_summary"]["Row"]

type PdfSummaryViewProps = {
  pdfSummary: PdfSummary,
};

export default function PdfSummaryView(props: PdfSummaryViewProps) {

  const [ selectedSummaryViewMode, setSelectedSummaryViewMode ] = useState(true);

  const color = "blue-500"
  const sharedButtonStyle = "px-4 py-2 border-blue-600 hover:ring-2";
  const selectedStyle = "bg-blue-600 text-white";
  const unselectedStyle = "text-blue-600 ";

  const summaryButtonStyle = `${sharedButtonStyle} ${selectedSummaryViewMode ? selectedStyle : unselectedStyle} border rounded-l-lg`;
  const viewPdfButtonStyle = `${sharedButtonStyle} ${!selectedSummaryViewMode ? selectedStyle : unselectedStyle} border-y border-r rounded-r-lg`;
  return (
    <div className="flex flex-col items-center">
      <div className="inline-flex roundeed-md text-sm shadow-sm" role="group">
        <button type="button"
          className={summaryButtonStyle}
          onClick={() => setSelectedSummaryViewMode(true)}>
          Summary
        </button>
        <button type="button"
          className={viewPdfButtonStyle}
          onClick={() => setSelectedSummaryViewMode(false)}>
          View PDF
        </button>
      </div>
      { !selectedSummaryViewMode && <PdfView />}
    </div>
  )
}