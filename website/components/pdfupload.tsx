
import React, { ChangeEvent, useState, } from "react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";


import { PdfMaker } from "./pdfmaker";
import { PdfElements, } from "../utils/sharedtypes";
import PdfSelected from "./pdfselected";
import { ClientDrawPath } from "../utils/sharedtypes";
import { SelectInPdfResponse } from "../utils/requestresponsetypes";
import { Database } from "../utils/database.types";
import { lambdaTriggerPdfProcessing } from "./AwsConnector";
import { useRouter } from "next/router";

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
  const supabase = useSupabaseClient<Database>();
  const [ pdfDocumentUrl, setPdfDocumentUrl ] = useState<string | undefined>(undefined);
  const [ pdfFileObj, setPdfFileObj ] = useState<File | null>(null);
  const [ pdfHash, setPdfHash ] = useState<string | null>(null);
  const [ pdfSelectedObjects, setPdfSelectedObjects ] = useState<PdfElements>([]);
  const router = useRouter();
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
        const pdfName = fileObj.name;
        setPdfFileObj(fileObj);
        setPdfDocumentUrl(url);
        const alreadyUploaded = await checkIfPdfAlreadyUploaded({ pdfId });
        if (!alreadyUploaded) {
          const uploadSuccess = await uploadPdf({ pdfId, bytes });
        }
        const alreadyProcessed = await checkIfPdfAlreadyProcessed({ pdfId, });
        if (!alreadyProcessed) {
          const processingTriggered = await triggerPdfProcessing({ pdfId, pdfName });
        }
        router.push(`/viewer/${pdfId}`);
        // to to /viewer/pdfId
      }
    }
    reader.readAsArrayBuffer(fileObj);
  }

  async function checkIfPdfAlreadyUploaded({
    pdfId,
  }: {
    pdfId: string
  }) {
    const { data, error } = await supabase.storage
      .from("pdfs")
      .list("public", {
        limit: 1,
        search: pdfId,
      }
    );
    if (error) {
      console.error("Failed to check if pdf already exists", error);
      return false;
    }
    console.log(data);
    return data.length > 0;
  }

  async function uploadPdf({
    pdfId,
    bytes,
  }: {
    pdfId: string,
    bytes: ArrayBuffer
  }) {
    const { error: uploadError } = await supabase.storage
      .from("pdfs")
      .upload(`public/${pdfId}.pdf`, bytes, { upsert: true });
    if (uploadError) {
      console.error("Failed to upload pdf:", uploadError);
      return false;
    }
  }

  async function insertPdfName({
    pdfId,
    pdfName,
  }: {
    pdfId: string,
    pdfName: string
  }) {
    const { error: insertError } = await supabase
      .from("pdf_summary")
      .upsert({
        pdf_id: pdfId,
        pdf_name: pdfName,
      })
    if (insertError) {
      console.error("Failed to insert pdf_summary", insertError);
    }
    console.log("Uploaded pdf");
    return true;
  }

  async function checkIfPdfAlreadyProcessed({
    pdfId,
  }: {
    pdfId: string,
  }) {
    const { data, error, status } = await supabase
      .from("pdf_summary")
      .select("*", { count: "exact", head: true })
      .eq("pdf_id", pdfId)
      .neq("pdf_summary", null)
      .single();
    if (error && status !== 406) {
      console.error("Failed to check if pdf already processed:", error, status);
      return false;
    }
    if (data) {
      console.log("Already processed:", data);
      return true;
    }
    console.log("406 error no rows", error);
    return false;
  }

  async function triggerPdfProcessing({
    pdfId,
    pdfName,
  }: {
    pdfId: string,
    pdfName: string,
  }) {
    await insertPdfName({ pdfId, pdfName });
    const { error: insertError } = await supabase
      .from("pdf_processing_progress")
      .upsert({
        pdf_id: pdfId,
        total_steps: 1,
        curr_step: 0,
        success: null,
      })
    if (insertError) {
      console.error("Failed to write to pdf_processing_progress", insertError);
    }
    const lambdaTriggered = await lambdaTriggerPdfProcessing(pdfId);
    return lambdaTriggered;
  }

  async function getContentFromDrawPaths(drawPaths: Array<ClientDrawPath>, page: number) {
    // TODO: Delete this function
    return;
  }

  // TODO: App upload button to Dynamdb using hash and pdfFile in FormData
  // TODO: Style colors like https://www.patterns.app/
  return (
    <div className="w-full text-center">
      <div className="flex m-5 items-center justify-center bg-grey-lighter">
        <label className="w-64 flex flex-col items-center px-4 py-6 bg-white text-blue-500 rounded-lg shadow-lg tracking-wide border border-blue cursor-pointer hover:bg-blue-500 hover:text-white">
            <svg className="w-8 h-8" fill="currentColor" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                <path d="M16.88 9.1A4 4 0 0 1 16 17H5a5 5 0 0 1-1-9.9V7a3 3 0 0 1 4.52-2.59A4.98 4.98 0 0 1 17 8c0 .38-.04.74-.12 1.1zM11 11h3l-4-4-4 4h3v3h2v-3z" />
            </svg>
            <span className="mt-2 text-base leading-normal">Upload PDF</span>
            <input
              className="hidden"
              type="file"
              accept=".pdf"
              onChange={onPdfFileChange} />
        </label>
      </div>
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