

import { useRouter } from "next/router";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import Layout from "../../components/Layout";
import { Database } from "../../utils/database.types";
import { useEffect, useState } from "react";
import { DatabaseTableNames } from "../../utils/tablenames.types";
import { lambdaTriggerPdfProcessing } from "../../components/AwsConnector";

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

  async function checkIfPdfAlreadyProcessed({
    pdfId,
  }: {
    pdfId: string,
  }) {
    const { data, error, status } = await supabase
      .from(DatabaseTableNames.PDF_SUMMARY)
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
    pdfId,
    pdfName,
  }: {
    pdfId: string,
    pdfName: string,
  }) {
    const alreadyProcessed = await checkIfPdfAlreadyProcessed({ pdfId, });
    if (!alreadyProcessed) {
      console.log("Waiting for db changes", pdfId, DatabaseTableNames.PDF_PROCESSING_PROGRESS);
      const channel = supabase.channel("db-changes");
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
          const processingTriggered = await triggerPdfProcessing({ pdfId, pdfName });
        }
      });
    }
  }

  useEffect(() => {
    onLoad({
      pdfId,
      pdfName,
    });
  }, [pdfId, pdfName]);

  async function getPdfSummary({
    pdfId,
  }: {
    pdfId: string,
  }): Promise<PdfSummary | boolean> {
    const { data, error, status } = await supabase
      .from("pdf_summary")
      .select()
      .eq("pdf_id", pdfId)
      .single();
    if (error && status !== 406) {
      console.error("Failed to get pdf summary already processed:", error, status);
      return false;
    }
    if (data) {
      return data;
    }
    console.log("406 error no rows", error);
    return false;
  }

  // TODO: PdfProgressingView https://supabase.com/docs/guides/realtime/quickstart#insert-and-receive-persisted-messages
  const progressView = (
    <div>
      { (pdfProcessingProgress.curr_step * 100 / pdfProcessingProgress.total_steps).toFixed(0) } %
    </div>
  );
  return (
    <Layout>
      <div>
        { JSON.stringify(router.query) }
      </div>
      <div>
        { !pdfProcessingProgress.success && progressView}
      </div>
      <div>
        Success: { String(pdfProcessingProgress.success) }
      </div>
      <div>
        { pdfProcessingProgress.msg}
      </div>

    </Layout>
  )

}