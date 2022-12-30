
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