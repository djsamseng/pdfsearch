
import { ChangeEvent, MouseEventHandler, MouseEvent, MutableRefObject, useRef, useState, useEffect, createContext } from "react";
import { usePdf } from "@mikecousins/react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";

import { PdfMaker, DrawPath } from "./pdfmaker";
import { PdfSelectedObjects } from "./pdfelementsdrawer";
import PdfSelected from "./pdfselected";

export default function PdfUpload() {
  const [ pdfDocumentUrl, setPdfDocumentUrl ] = useState<string | undefined>(undefined);
  const [ pdfFileObj, setPdfFileObj ] = useState<File | null>(null);
  const [ pdfSelectedObjects, setPdfSelectedObjects ] = useState<PdfSelectedObjects | null>(null);
  function onPdfFileChange(evt: ChangeEvent<HTMLInputElement>) {
    const fileObj = evt.target.files && evt.target.files[0];
    console.log(fileObj);
    if (!fileObj) {
      return;
    }
    const url = URL.createObjectURL(fileObj);
    setPdfFileObj(fileObj);
    setPdfDocumentUrl(url);
  }
  async function getContentFromDrawPaths(drawPaths: Array<DrawPath>, page: number) {
    const formData = new FormData();
    if (!pdfFileObj) {
      console.error("No pdf file to upload");
      return;
    }
    formData.append("pdfFile", pdfFileObj)
    formData.append("drawPaths", JSON.stringify(drawPaths));
    formData.append("pageNumber", String(page))
    const resp = await fetch("http://localhost:5000/searchpdf", {
      method: "post",
      body: formData,
    });
    const json = await resp.json();
    console.log("Got resp:", json);
    if ("searchPaths" in json) {
      setPdfSelectedObjects(json);
    }
  }

  return (
    <div className="w-full text-center">
      <input type="file" accept=".pdf" onChange={onPdfFileChange} />
      { pdfDocumentUrl && pdfFileObj && (
        <PdfMaker pdfDocumentUrl={pdfDocumentUrl} pdfFileObj={pdfFileObj} getContentFromDrawPaths={getContentFromDrawPaths} />
      )}
      { pdfSelectedObjects && (
        <PdfSelected elems={pdfSelectedObjects} />
      )}
    </div>
  )
}