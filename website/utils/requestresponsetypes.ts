
import { ClientDrawPath, PdfElements } from "./sharedtypes";

type SelectInPdfRequest = {
  pdfFile: File;
  drawPaths: Array<ClientDrawPath>;
  page: string;
}; // Send as Form so type not adhered to
export type SelectInPdfResponse = {
  selectedPaths: PdfElements;
  searchRequestData: PdfElements;
}

export type PdfJsonResponse = {
  label: string | null;
  bbox: [number, number, number, number];
}

export type PdfSummaryJson = {
  //             pageNumber,     class,         elemId, list
  windows: Record<string, Record<string, Record<string, PdfJsonResponse[]>>>;
  doors: Record<string, Record<string, Record<string, PdfJsonResponse[]>>>;
  houseName: string;
  architectName: string;
  pageNames: Record<number, string>;
}

export type CompletePdfSummary = {
  pdfId: string;
  pdfName: string;
  pdfSummary: PdfSummaryJson;
}