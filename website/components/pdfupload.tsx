
import React, { ChangeEvent, useState, } from "react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";


import { PdfMaker } from "./pdfmaker";
import { PdfElements, } from "../utils/sharedtypes";
import PdfSelected from "./pdfselected";
import { ClientDrawPath } from "../utils/sharedtypes";
import { SelectInPdfResponse } from "../utils/requestresponsetypes";
import { Database } from "../utils/database.types";
import { lambdaTriggerPdfProcessing } from "./AwsConnector";

type PdfSummary = Database["public"]["Tables"]["pdf_summary"]["Row"]
type PdfProcessingProgress = Database["public"]["Tables"]["pdf_processing_progress"]["Row"]

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
        const alreadyUploaded = await checkIfPdfAlreadyUploaded(pdfId);
        if (!alreadyUploaded) {
          const uploadSuccess = await uploadPdf(pdfId, pdfName, bytes);
        }
        const alreadyProcessed = await checkIfPdfAlreadyProcessed(pdfId);
        if (!alreadyProcessed) {
          // First write to pdf_processing_progress
          const processingTriggered = await triggerPdfProcessing(pdfId);
        }
      }
    }
    reader.readAsArrayBuffer(fileObj);
  }

  async function checkIfPdfAlreadyUploaded(pdfId: string) {
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

  async function uploadPdf(pdfId: string, pdfName: string, bytes: ArrayBuffer) {
    const { error: uploadError } = await supabase.storage
      .from("pdfs")
      .upload(`public/${pdfId}.pdf`, bytes, { upsert: true });
    if (uploadError) {
      console.error("Failed to upload pdf:", uploadError);
      return false;
    }
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

  async function checkIfPdfAlreadyProcessed(pdfId: string) {
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

  async function triggerPdfProcessing(pdfId: string) {
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