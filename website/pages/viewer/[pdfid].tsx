
import { useRouter } from "next/router";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import Layout from "../../components/Layout";
import { Database } from "../../utils/database.types";
import React, { useEffect, useState } from "react";
import { DatabaseTableNames } from "../../utils/tablenames.types";
import { DataAccessor } from "../../utils/DataAccessor";
import { lambdaTriggerPdfProcessing } from "../../components/AwsConnector";
import { RealtimeChannel } from "@supabase/supabase-js";
import PdfSummaryView from "../../components/PdfSummaryView";
import NavBreadcrumb from "../../components/NavBreadcrumb";
import Link from "next/link";
import { CompletePdfSummary } from "../../utils/requestresponsetypes";
import { LoadingSpinner } from "../../components/LoadingSpinner";

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
  const [ pdfSummary, setPdfSummary ] = useState<CompletePdfSummary | null>(null);

  useEffect(() => {
    console.log("Created channel");
    const channel = supabase.channel("db-changes");
    function cleanupSubscription() {
      console.log("Cleaning up subscription:", !!taskListener);
      taskListener?.unsubscribe();
      supabase.removeChannel(channel);
    }
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
    async function loadExistingSummaryIfProcessed({
      pdfId,
    }: {
      pdfId: string,
    }) {
      const fetchedPdfSummary = await DataAccessor.instance.getPdfSummaryIfProcessed({
        supabase,
        pdfId,
      });
      if (fetchedPdfSummary && typeof fetchedPdfSummary.pdf_summary === "string") {
        setPdfProcessingProgress({
          curr_step: 0,
          msg: "Already processed",
          pdf_id: pdfId,
          success: true,
          total_steps: 1,
        });
        const completePdfSummary: CompletePdfSummary = {
          pdfId: fetchedPdfSummary.pdf_id,
          pdfName: fetchedPdfSummary.pdf_name,
          pdfSummary: JSON.parse(fetchedPdfSummary.pdf_summary as string),
        }
        setPdfSummary(completePdfSummary);
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
          if (alreadyProcessedPdf) {
            console.log("Already processed pdf and has summary");
            // Cleanup
            cleanupSubscription();
          }
          else {
            const alreadyProcessing =  await DataAccessor.instance.getPdfProcessingProgress({
              supabase,
              pdfId,
            });
            if (alreadyProcessing) {
              console.log("Already processing pdf. Waiting");
              setPdfProcessingProgress(alreadyProcessing);
              // Don't cleanup
            }
            else {
              const res = await triggerPdfProcessing({ pdfId, pdfName });
              console.log("triggerPdfProccesing res:", res);
              // Don't cleanup
            }
          }
        }
        catch (error) {
          console.error("lambda error:", error);
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
    <>
      <div className="w-full px-4">
        <NavBreadcrumb links={[{
          text: "Home",
          href: "/",
          icon: (
            <svg aria-hidden="true" className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
              <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"></path>
            </svg>
          )
        }, {
          text: "My PDFs",
          href: "/",
          icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" >
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
            </svg>
          )
        }, {
          text: pdfSummary?.pdfName || "",
          href: "",
        }]}/>
      </div>
      <div className="my-3">
        <span className="text-2xl">{ pdfName }</span>
      </div>
      { pdfProcessingProgress.success === null && (
        <div>
          <div>
            <LoadingSpinner text={`Processing PDF ${pdfProcessingProgress.curr_step} / ${pdfProcessingProgress.total_steps}`} />
          </div>
          <div>
            {pdfProcessingProgress.msg}
          </div>
        </div>
      )}
      { pdfProcessingProgress.success === false && (
        <>
          <div>
            Failed to process PDF
          </div>
          <div>
            { pdfProcessingProgress.msg }
          </div>
        </>
      )}

      <div className="w-full">
        { pdfProcessingProgress.success === null && progressView}
        { pdfProcessingProgress.success === true && pdfSummary && <PdfSummaryView pdfSummary={pdfSummary} /> }
        { pdfProcessingProgress.success === false && <></>}
      </div>
    </>
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
      <Layout>
        Unknown pdf { pdfId } { pdfName }
      </Layout>
    )
  }
  return (
    <Layout>
      <PdfIdViewer pdfId={pdfId} pdfName={pdfName} />
    </Layout>
  );
}

const fullLayout = () => {
  return (
    <Layout>
      <PdfIdViewer> subscribe, loadExisting, triggerProcessing, loadExisting, unsubscribe
        <BackIcon />
        <PdfName />
        <ProcessingMsg />
        <PdfSummaryView> selectViewMode
          Summary ViewPdf
          <PdfView> getPdfBytes
            <PdfViewer> canvasMouseEvents
              Previous Next Zoom + Zoom -
              <canvas />
            </PdfViewer>
          </PdfView>
        </PdfSummaryView>
      </PdfIdViewer>
    </Layout>
  )
}