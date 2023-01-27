
import React from "react";

export type PdfViewContextType = {
  page: number;
  setPage: (newPage: number) => void;
  bbox: [number, number, number, number] | null;
  setBbox: (newBbox: [number, number, number, number] | null) => void;
  zoom: number | null;
  setZoom: (newZoom: number | null) => void;
  pdfSize: { width: number; height: number } | null;
  setPdfSize: (newPdfSize: { width: number; height: number}) => void;
}
export const PdfViewContext = React.createContext<PdfViewContextType>({
  page: 1,
  setPage: (newPage: number) => {},
  bbox: null,
  setBbox: (newBbox: [number, number, number, number] | null) => {},
  zoom: null,
  setZoom: (newZoom: number | null) => {},
  pdfSize: null,
  setPdfSize: (newPdfSize: { width: number; height: number}) => {},
})