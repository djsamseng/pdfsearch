

import { useRouter } from "next/router";
import { useSupabaseClient } from "@supabase/auth-helpers-react";

import Layout from "../../components/Layout";
import { Database } from "../../utils/database.types";

type PdfSummary = Database["public"]["Tables"]["pdf_summary"]["Row"]
type PdfProcessingProgress = Database["public"]["Tables"]["pdf_processing_progress"]["Row"]

export default function PdfIdViewer() {
  const router = useRouter();
  const supabase = useSupabaseClient<Database>();

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
  return (
    <Layout>
      { JSON.stringify(router.query) }
    </Layout>
  )

}