
import { ChangeEvent, MouseEventHandler, MouseEvent, MutableRefObject, useRef, useState, useEffect, createContext } from "react";
import { usePdf } from "@mikecousins/react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";

import { PdfMaker } from "./pdfmaker";

export default function PdfUpload() {
  const [ pdfDocumentUrl, setPdfDocumentUrl ] = useState<string | undefined>(undefined);
  const canvasRef = useRef(null);
  function onPdfFileChange(evt: ChangeEvent<HTMLInputElement>) {
    const fileObj = evt.target.files && evt.target.files[0];
    console.log(fileObj);
    if (!fileObj) {
      return;
    }
    const url = URL.createObjectURL(fileObj);
    setPdfDocumentUrl(url);
  }

  return (
    <div className="w-full text-center">
      <input type="file" accept=".pdf" onChange={onPdfFileChange} />
      { pdfDocumentUrl && (
        <PdfMaker pdfDocumentUrl={pdfDocumentUrl} />
      )}
    </div>
  )
}