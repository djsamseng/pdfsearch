
import React from "react";

export type PdfViewContextType = {
  page: number;
  setPage: (newPage: number) => void;
  bbox: [number, number, number, number] | null;
  setBbox: (newBbox: [number, number, number, number] | null) => void;
}
export const PdfViewContext = React.createContext<PdfViewContextType>({
  page: 1,
  setPage: (newPage: number) => {},
  bbox: null,
  setBbox: (newBbox: [number, number, number, number] | null) => {},
});
