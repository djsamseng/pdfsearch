

import { useRouter } from "next/router";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import Layout from "../../components/Layout";
import { Database } from "../../utils/database.types";
import { useEffect, useState } from "react";
import { DatabaseTableNames } from "../../utils/tablenames.types";
import { lambdaTriggerPdfProcessing } from "../../components/AwsConnector";
import { RealtimeChannel } from "@supabase/supabase-js";
import PdfSummaryView from "../../components/PdfSummaryView";
import Link from "next/link";

type PdfSummary = Database["public"]["Tables"]["pdf_summary"]["Row"]
type PdfProcessingProgress = Database["public"]["Tables"]["pdf_processing_progress"]["Row"]

export default function PdfIdViewer() {
  const router = useRouter();
  const supabase = useSupabaseClient<Database>();

  const {
    pdfid: pdfId,
    pdfname: pdfName,
  } = router.query;
  if (!(pdfId && typeof pdfId === "string" && pdfId.length > 0) ||
      !(pdfName && typeof pdfName === "string" && pdfName.length > 0)) {
    return (
      <div>
        Unknown pdf { pdfId } { pdfName }
      </div>
    )
  }

  const [ pdfProcessingProgress, setPdfProcessingProgress ] = useState<PdfProcessingProgress>({
    curr_step: 0,
    msg: null,
    pdf_id: pdfId,
    success: null,
    total_steps: 1,
  });
  const [ pdfSummary, setPdfSummary ] = useState<PdfSummary | null>(null);

  async function getPdfSummaryIfProcessed({
    pdfId,
  }: {
    pdfId: string,
  }) {
    const { data, error, status } = await supabase
      .from(DatabaseTableNames.PDF_SUMMARY)
      .select()
      .eq("pdf_id", pdfId)
      .single();
    if (error && status !== 406) {
      console.error("Failed to check if pdf already processed:", error, status);
      return false;
    }
    if (data && data.pdf_summary !== null) {
      console.log("pdf summary not null:", data);
      return data;
    }
    console.log("406 error no rows - already processed", error);
    return false;
  }

  async function insertPdfName({
    pdfId,
    pdfName,
  }: {
    pdfId: string,
    pdfName: string
  }) {
    const { error: insertError } = await supabase
      .from(DatabaseTableNames.PDF_SUMMARY)
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

  async function triggerPdfProcessing({
    pdfId,
    pdfName,
  }: {
    pdfId: string,
    pdfName: string,
  }) {
    await insertPdfName({ pdfId, pdfName });
    const { error: insertError } = await supabase
      .from(DatabaseTableNames.PDF_PROCESSING_PROGRESS)
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

  async function onLoad({
    channel,
    pdfId,
    pdfName,
  }: {
    channel: RealtimeChannel,
    pdfId: string,
    pdfName: string,
  }) {
    const fetchedPdfSummary = await getPdfSummaryIfProcessed({ pdfId, });
    if (fetchedPdfSummary) {
      setPdfProcessingProgress({
        curr_step: 0,
        msg: "Already processed",
        pdf_id: pdfId,
        success: true,
        total_steps: 1,
      });
      setPdfSummary(fetchedPdfSummary);
    }
    else {
      channel.on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: DatabaseTableNames.PDF_PROCESSING_PROGRESS,
          filter: `pdf_id=eq.${pdfId}`
        }, (payload) => {
          const newStatus = payload.new as PdfProcessingProgress;
          setPdfProcessingProgress(newStatus);
          if (newStatus.success !== null) {
            supabase.removeChannel(channel);
          }
        });
      channel.subscribe(async (status) => {
        if (status === "SUBSCRIBED") {
          console.log("Waiting for db changes", pdfId, DatabaseTableNames.PDF_PROCESSING_PROGRESS);
          const processingTriggered = await triggerPdfProcessing({ pdfId, pdfName });
        }
      });
    }
  }

  useEffect(() => {
    const channel = supabase.channel("db-changes");
    onLoad({
      channel,
      pdfId,
      pdfName,
    });

    return () => {
      supabase.removeChannel(channel)
    }
  }, [pdfId, pdfName]);

  const progressView = (
    <div>
      { (pdfProcessingProgress.curr_step * 100 / pdfProcessingProgress.total_steps).toFixed(0) } %
    </div>
  );
  return (
    <Layout>
      <div className="w-full max-w-2xl">
        <Link href="/" className="text-blue-600 flex flex-row">
          {/* https://heroicons.com/ */}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          <span>Back</span>
        </Link>
      </div>
      <div className="mb-3 -mt-3">
        <span className="text-2xl">{ pdfName }</span>
      </div>
      <div>
        Success: { String(pdfProcessingProgress.success) }
      </div>
      <div>
        { pdfProcessingProgress.msg}
      </div>
      <div>
        { pdfProcessingProgress.success === null && progressView}
        { pdfProcessingProgress.success === true && pdfSummary && <PdfSummaryView pdfSummary={pdfSummary} /> }
        { pdfProcessingProgress.success === false && <></>}
      </div>


    </Layout>
  )

}