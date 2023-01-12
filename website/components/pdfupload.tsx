
import React, { ChangeEvent, MouseEventHandler, MouseEvent, MutableRefObject, useRef, useState, useEffect, createContext } from "react";
import { usePdf } from "@mikecousins/react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";

import { PdfMaker } from "./pdfmaker";
import { PdfElements, } from "../utils/sharedtypes";
import PdfSelected from "./pdfselected";
import { ClientDrawPath } from "../utils/sharedtypes";
import { SelectInPdfResponse } from "../utils/requestresponsetypes";
import { AwsConnectorContext, triggerPdfProcessing } from '../components/AwsConnector';

async function sha256(message: string) {
  // encode as UTF-8
  const msgBuffer = new TextEncoder().encode(message);

  // hash the message
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);

  // convert ArrayBuffer to Array
  const hashArray = Array.from(new Uint8Array(hashBuffer));

  // convert bytes to hex string
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}


export default function PdfUpload() {
  const [ pdfDocumentUrl, setPdfDocumentUrl ] = useState<string | undefined>(undefined);
  const [ pdfFileObj, setPdfFileObj ] = useState<File | null>(null);
  const [ pdfHash, setPdfHash ] = useState<string | null>(null);
  const [ pdfSelectedObjects, setPdfSelectedObjects ] = useState<PdfElements>([]);
  const { processPdfLoadingStatus, setProcessPdfLoadingStatus } = React.useContext(AwsConnectorContext);
  function onPdfFileChange(evt: ChangeEvent<HTMLInputElement>) {
    const fileObj = evt.target.files && evt.target.files[0];
    console.log(fileObj);
    if (!fileObj) {
      return;
    }
    const reader = new FileReader();
    reader.onload = async (evt) => {
      const bytes = evt.target && evt.target.result;
      if (bytes instanceof ArrayBuffer) {
        // TODO: window.crypto may not be in old browsers
        const hashBuffer = await window.crypto.subtle.digest("SHA-256", bytes);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const pdfId = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
        setPdfHash(pdfId);
        const url = URL.createObjectURL(fileObj);
        setPdfFileObj(fileObj);
        setPdfDocumentUrl(url);
        const alreadyUploaded = await checkIfPdfAlreadyUploaded(pdfId);
        if (!alreadyUploaded) {
          const uploadSuccess = await uploadPdf(pdfId, bytes);
          if (uploadSuccess) {
            const processingTriggered = await triggerPdfProcessing(pdfId, setProcessPdfLoadingStatus);
          }
        }
      }
    }
    reader.readAsArrayBuffer(fileObj);
  }

  async function checkIfPdfAlreadyUploaded(pdfId: string) {
    return false;
  }

  async function uploadPdf(pdfId: string, bytes: ArrayBuffer) {
    return true;
  }

  async function getContentFromDrawPaths(drawPaths: Array<ClientDrawPath>, page: number) {
    // TODO: Delete this function
    const formData = new FormData();
    if (!pdfFileObj) {
      console.error("No pdf file to upload");
      return;
    }
    // Matches requestresponsetypes.ts SelectInPdfRequest
    formData.append("pdfFile", pdfFileObj)
    formData.append("drawPaths", JSON.stringify(drawPaths));
    formData.append("pageNumber", String(page))
    // http://localhost:5000/selectinpdf
    try {
      const resp = await fetch("http://127.0.0.1:5000/selectinpdf", {
        method: "post",
        body: formData,
      });
      const json = await resp.json() as SelectInPdfResponse;
      console.log("Got resp:", json);
      if ("selectedPaths" in json) {
        setPdfSelectedObjects(json.selectedPaths);
      }
    }
    catch (error) {
      console.error(error);
    }

  }

  // TODO: App upload button to Dynamdb using hash and pdfFile in FormData
  return (
    <div className="w-full text-center">
      <input type="file" accept=".pdf" onChange={onPdfFileChange} />
      { pdfDocumentUrl && pdfFileObj && (
        <PdfMaker pdfDocumentUrl={pdfDocumentUrl}
          pdfFileObj={pdfFileObj}
          getContentFromDrawPaths={getContentFromDrawPaths} />
      )}
      { pdfSelectedObjects.length > 0 && (
        <PdfSelected elems={pdfSelectedObjects} />
      )}
    </div>
  )
}