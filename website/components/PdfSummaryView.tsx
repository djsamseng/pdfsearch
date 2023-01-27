

import { useState } from "react";
import { Database } from "../utils/database.types";

import PdfView from "./PdfView";
import { CompletePdfSummary } from "../utils/requestresponsetypes";
import SummaryElementList from "./SummaryElementList";
import { PdfViewContext } from "./PdfViewContext";

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
  const [ jumpToPositionEnabled, setJumpToPositionEnabled ] = useState(true);
  const [ page, setPage ] = useState(1);
  const [ bbox, setBbox ] = useState<[number, number, number, number] | null>(null);
  const [ zoom, setZoom ] = useState<number | null>(0.4);
  const [ pdfSize, setPdfSize ] = useState<{ width: number; height: number;} | null>(null);
  const pdfViewContextProvider = {
    page,
    setPage: (newPage: number) => setPage(newPage),
    bbox,
    setBbox: (newBbox: [number, number, number, number] | null) => setBbox(newBbox),
    zoom,
    setZoom: (newZoom: number | null) => setZoom(newZoom),
    pdfSize,
    setPdfSize: (newSize: { width: number; height: number}) => setPdfSize(newSize),
  };

  function setJumpToPosition(args: {
    page: number;
    bbox: [number, number, number, number]
  }) {
    if (jumpToPositionEnabled) {
      // Page starts from 1
      setPage(args.page + 1);
      setZoom(null);
      setBbox(args.bbox);
    }
  }


  // https://flowbite.com/docs/getting-started/introduction/
  const sharedButtonStyle = "px-4 py-2 border-blue-600 hover:ring-2";
  const selectedStyle = "bg-blue-600 text-white";
  const unselectedStyle = "text-blue-600 ";

  const summaryButtonStyle = `${sharedButtonStyle} ${summaryViewMode === PdfSummaryMode.SUMMARY ? selectedStyle : unselectedStyle} border rounded-l-lg`;
  const splitModeButtonStyle = `${sharedButtonStyle} ${summaryViewMode === PdfSummaryMode.SPLIT ? selectedStyle : unselectedStyle} border-y border-r`;
  const viewPdfButtonStyle = `${sharedButtonStyle} ${summaryViewMode === PdfSummaryMode.PDF ? selectedStyle : unselectedStyle} border-y border-r rounded-r-lg`;
  return (
    <PdfViewContext.Provider value={pdfViewContextProvider}>
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
            <SummaryElementList pdfSummary={pdfSummary} setJumpToPosition={setJumpToPosition}/>
          )}
          { summaryViewMode === PdfSummaryMode.SPLIT && (
            <div className="grid grid-cols-2 gap-4">
              <SummaryElementList pdfSummary={pdfSummary} setJumpToPosition={setJumpToPosition} />
              <div className="text-center">
                <div onClick={() => setJumpToPositionEnabled(!jumpToPositionEnabled)} >
                  <input id="jumpToOnHoverRadio" type="radio" checked={jumpToPositionEnabled} onChange={() => {}} />
                  <label className="mx-2">Jump To Results</label>
                </div>
                <PdfView pdfSummary={pdfSummary} smallCanvas={true} />
              </div>
            </div>
          )}
          { summaryViewMode === PdfSummaryMode.PDF && (
            <PdfView pdfSummary={pdfSummary} smallCanvas={false} />
          )}
        </div>

      </div>
    </PdfViewContext.Provider>
  )
}