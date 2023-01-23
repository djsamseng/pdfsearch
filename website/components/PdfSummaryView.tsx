

import { useState } from "react";
import { Database } from "../utils/database.types";

import PdfView from "./PdfView";
import { CompletePdfSummary } from "../utils/requestresponsetypes";
import SummaryElementList from "./SummaryElementList";

export default function PdfSummaryView({
  pdfSummary,
}: {
  pdfSummary: CompletePdfSummary;
}) {

  const [ selectedSummaryViewMode, setSelectedSummaryViewMode ] = useState(true);

  // https://flowbite.com/docs/getting-started/introduction/
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
      <div className="">
        { selectedSummaryViewMode && (
          <div className="grid grid-cols-2 gap-4">
            <SummaryElementList pdfSummary={pdfSummary} />
            <PdfView pdfSummary={pdfSummary} smallCanvas={selectedSummaryViewMode} />
          </div>
        )}
        { !selectedSummaryViewMode && (
          <PdfView pdfSummary={pdfSummary} smallCanvas={selectedSummaryViewMode} />
        )}
      </div>

    </div>
  )
}