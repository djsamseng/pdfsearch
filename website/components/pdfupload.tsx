
import React, { ChangeEvent, useState, } from "react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import { Database } from "../utils/database.types";
import { useRouter } from "next/router";
import { LoadingSpinner } from "./LoadingSpinner";

export default function PdfUpload() {
  const supabase = useSupabaseClient<Database>();
  const [ isUploading, setIsUploading ] = useState(false);
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
        try {
          setIsUploading(true);
          // TODO: window.crypto may not be in old browsers
          const hashBuffer = await window.crypto.subtle.digest("SHA-256", bytes);
          const hashArray = Array.from(new Uint8Array(hashBuffer));
          const pdfId = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
          const pdfName = fileObj.name;
          const alreadyUploaded = await checkIfPdfAlreadyUploaded({ pdfId });
          if (!alreadyUploaded) {
            const uploadSuccess = await uploadPdf({ pdfId, bytes });
            if (!uploadSuccess) {
              console.log("Failed to upload");
            }
          }
          router.push(`/viewer/${pdfId}?pdfname=${pdfName}`);
        }
        catch (error) {
          console.error("Failed to upload:", error);
        }
        finally {
          setIsUploading(false);
        }
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

  // TODO: App upload button to Dynamdb using hash and pdfFile in FormData
  // TODO: Style colors like https://www.patterns.app/
  return (
    <div className="w-full text-center">
      <div className="flex m-5 items-center justify-center bg-grey-lighter">
        <label className="w-64 flex flex-col items-center px-4 py-6 bg-white text-blue-500 rounded-lg shadow-lg tracking-wide border border-blue cursor-pointer hover:bg-blue-500 hover:text-white">
          { isUploading && (
            <>
              <LoadingSpinner text="Uploading" />
            </>
          )}
          { !isUploading && (
            <>
              <svg className="w-8 h-8" fill="currentColor" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                <path d="M16.88 9.1A4 4 0 0 1 16 17H5a5 5 0 0 1-1-9.9V7a3 3 0 0 1 4.52-2.59A4.98 4.98 0 0 1 17 8c0 .38-.04.74-.12 1.1zM11 11h3l-4-4-4 4h3v3h2v-3z" />
              </svg>
              <span className="mt-2 text-base leading-normal">Upload PDF</span>
              <input
                className="hidden"
                type="file"
                accept=".pdf"
                onChange={onPdfFileChange} />
            </>
          )}
        </label>
      </div>
    </div>
  )
}