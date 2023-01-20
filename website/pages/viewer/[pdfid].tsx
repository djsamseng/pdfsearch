
import { useCallback } from "react";
import { useRouter } from "next/router";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import Layout from "../../components/Layout";
import { Database } from "../../utils/database.types";
import { useEffect, useState } from "react";
import { DatabaseTableNames } from "../../utils/tablenames.types";
import { DataAccessor } from "../../utils/DataAccessor";
import { lambdaTriggerPdfProcessing } from "../../components/AwsConnector";
import { RealtimeChannel } from "@supabase/supabase-js";
import PdfSummaryView from "../../components/PdfSummaryView";
import Link from "next/link";

type PdfSummary = Database["public"]["Tables"]["pdf_summary"]["Row"]
type PdfProcessingProgress = Database["public"]["Tables"]["pdf_processing_progress"]["Row"]

function PdfIdViewer({
  pdfId,
  pdfName,
}: {
  pdfId: string,
  pdfName: string,
}) {

  const supabase = useSupabaseClient<Database>();

  const [ pdfProcessingProgress, setPdfProcessingProgress ] = useState<PdfProcessingProgress>({
    curr_step: 0,
    msg: null,
    pdf_id: pdfId,
    success: null,
    total_steps: 1,
  });
  const [ pdfSummary, setPdfSummary ] = useState<PdfSummary | null>(null);

  async function triggerPdfProcessing({
    pdfId,
    pdfName,
  }: {
    pdfId: string,
    pdfName: string,
  }) {
    await DataAccessor.instance.insertPdfName({ supabase, pdfId, pdfName });
    await DataAccessor.instance.createPdfProccessing({ supabase, pdfId, });
    const lambdaTriggered = await lambdaTriggerPdfProcessing(pdfId);
    return lambdaTriggered;
  }

  useEffect(() => {
    console.log("Created channel");
    const channel = supabase.channel("db-changes");
    function cleanupSubscription() {
      taskListener?.unsubscribe();
      supabase.removeChannel(channel);
    }
    async function loadExistingSummaryIfProcessed({
      pdfId,
    }: {
      pdfId: string,
    }) {
      const fetchedPdfSummary = await DataAccessor.instance.getPdfSummaryIfProcessed({ supabase, pdfId, });
      if (fetchedPdfSummary) {
        setPdfProcessingProgress({
          curr_step: 0,
          msg: "Already processed",
          pdf_id: pdfId,
          success: true,
          total_steps: 1,
        });
        setPdfSummary(fetchedPdfSummary);
        return true;
      }
      else {
        return false;
      }
    }
    channel.on(
      "postgres_changes",
      {
        event: "UPDATE",
        schema: "public",
        table: DatabaseTableNames.PDF_PROCESSING_PROGRESS,
        filter: `pdf_id=eq.${pdfId}`
      }, async (payload) => {
        console.log("Got new status:", payload.new);
        const newStatus = payload.new as PdfProcessingProgress;
        setPdfProcessingProgress(newStatus);
        if (newStatus.success !== null) {

          DataAccessor.instance.mutateAllPdfSummary();
          try {
            const loaded = await loadExistingSummaryIfProcessed({ pdfId });
            if (!loaded) {
              throw new Error("Failed to get pdf summary after processing");
            }
          }
          catch (error) {
            console.error("Failed to load pdf summary after processing:", error);
          }
        }
      });
    const taskListener = channel.subscribe(async (status) => {
      console.log("Channel status:", status);
      if (status === "SUBSCRIBED") {
        console.log("Waiting for db changes", pdfId, DatabaseTableNames.PDF_PROCESSING_PROGRESS);
        try {
          const alreadyProcessedPdf = await loadExistingSummaryIfProcessed({
            pdfId,
          });
          if (!alreadyProcessedPdf) {
            const res = await triggerPdfProcessing({ pdfId, pdfName });
            console.log("lambda response:", res);
          }
        }
        catch (error) {
          console.error("lambda error:", error);
        }
        finally {
          cleanupSubscription();
        }
      }
    });

    return () => {
      cleanupSubscription();
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

export default function PdfId() {
  const router = useRouter();
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
  return (
    <PdfIdViewer pdfId={pdfId} pdfName={pdfName} />
  );
}