
import { ChangeEvent, MouseEventHandler, MouseEvent, MutableRefObject, useRef, useState, useEffect, createContext } from "react";
import { usePdf } from "@mikecousins/react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";

import { PdfMaker } from "./pdfmaker";
import { PdfElements, } from "../utils/sharedtypes";
import PdfSelected from "./pdfselected";
import { ClientDrawPath } from "../utils/sharedtypes";
import { SelectInPdfResponse } from "../utils/requestresponsetypes";

export default function PdfUpload() {
  const [ pdfDocumentUrl, setPdfDocumentUrl ] = useState<string | undefined>(undefined);
  const [ pdfFileObj, setPdfFileObj ] = useState<File | null>(null);
  const [ pdfSelectedObjects, setPdfSelectedObjects ] = useState<PdfElements>([]);
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
  async function getContentFromDrawPaths(drawPaths: Array<ClientDrawPath>, page: number) {
    const formData = new FormData();
    if (!pdfFileObj) {
      console.error("No pdf file to upload");
      return;
    }
    // Matches requestresponsetypes.ts SelectInPdfRequest
    formData.append("pdfFile", pdfFileObj)
    formData.append("drawPaths", JSON.stringify(drawPaths));
    formData.append("pageNumber", String(page))
    const resp = await fetch("http://localhost:5000/selectinpdf", {
      method: "post",
      body: formData,
    });
    const json = await resp.json() as SelectInPdfResponse;
    console.log("Got resp:", json);
    if ("selectedPaths" in json) {
      setPdfSelectedObjects(json.selectedPaths);
    }
  }

  return (
    <div className="w-full text-center">
      <input type="file" accept=".pdf" onChange={onPdfFileChange} />
      { pdfDocumentUrl && pdfFileObj && (
        <PdfMaker pdfDocumentUrl={pdfDocumentUrl} pdfFileObj={pdfFileObj} getContentFromDrawPaths={getContentFromDrawPaths} />
      )}
      { pdfSelectedObjects.length > 0 && (
        <PdfSelected elems={pdfSelectedObjects} />
      )}
    </div>
  )
}