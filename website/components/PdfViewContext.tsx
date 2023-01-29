
import React from "react";

export type PdfViewContextType = {
  page: number;
  setPage: (newPage: number) => void;
  bboxes: [number, number, number, number][] | null;
  setBboxes: (newBboxes: [number, number, number, number][] | null) => void;
}
export const PdfViewContext = React.createContext<PdfViewContextType>({
  page: 1,
  setPage: (newPage: number) => {},
  bboxes: null,
  setBboxes: (newBboxes: [number, number, number, number][] | null) => {},
});
