
import { useRef, useState, MouseEvent, useEffect } from "react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";
import * as PdfJS  from "pdfjs-dist/build/pdf"
import useSWR from "swr";

import { DataAccessor } from "../utils/DataAccessor";
import { usePdf } from "../utils/UsePdf";
import { Database } from "../utils/database.types";
import { CompletePdfSummary } from "../utils/requestresponsetypes";

enum CanvasMouseEvents {
  MOVE = "MOVE",
  DOWN = "DOWN",
  UP = "UP",
  OUT = "OUT",
}

function PdfViewer({
  pdfData,
  smallCanvas,
}: {
  pdfData: ArrayBuffer;
  smallCanvas: boolean;
}) {
  // TODO: https://github.com/mozilla/pdf.js/blob/master/examples/learning/helloworld64.html#L42
  // And replace https://github.com/mikecousins/react-pdf-js/blob/9b0be61ea478042727f11328ca1b27ecd8b4e411/packages/react-pdf-js/src/index.tsx#L92
  const canvasRef = useRef(null)
  const [ page, setPage ] = useState(1);
  const [ scale, setScale ] = useState(0.4);
  const flag = useRef(false);

  const { pdfDocument, pdfPage } = usePdf({
    pdfData,
    page,
    canvasRef,
    scale,
    onPageRenderSuccess: async (page) => {
      console.log("Rendered pdf");
    },
  })

  function increaseZoom() {
    setScale(scale * 1.1);
  }
  function decreaseZoom() {
    setScale(scale * 0.9);
  }
  function onCanvasMouse(name: CanvasMouseEvents, evt: MouseEvent) {
    const canvas = canvasRef.current as HTMLCanvasElement | null;
    if (!canvas) {
      return;
    }
    if (!canvas.parentElement) {
      return;
    }
    const parentRect = canvas.getBoundingClientRect();
    const canvasX = (evt.clientX - parentRect.left);
    const canvasY = (evt.clientY - parentRect.top);
    const pdfX = (canvasX + canvas.scrollLeft) / scale;
    const pdfY = (canvasY + canvas.scrollTop) / scale;
    if (name === CanvasMouseEvents.MOVE) {
      if (evt.buttons) {
        canvas.parentElement.scrollTop -= evt.movementY;
        canvas.parentElement.scrollLeft -= evt.movementX;
      }
    }
    else if (name === CanvasMouseEvents.DOWN) {
    }
    else if (name === CanvasMouseEvents.UP) {
      flag.current = false;
    }
    else if (name === CanvasMouseEvents.OUT) {
      flag.current = false;
    }
  }

  const buttonStyle = "rounded px-2 py-2 rounded-none first:rounded-l last:rounded-r border-r last:border-r-0 hover:bg-gray-200 first:hover:bg-gray-300";
  const buttonStyleActive = "bg-blue-100 border-2 rounded px-2 py-1";
  const canvasElem = (
    <canvas ref={canvasRef} className={"cursor-grab" }
          onMouseMove={(evt) => onCanvasMouse(CanvasMouseEvents.MOVE, evt)}
          onMouseDown={(evt) => onCanvasMouse(CanvasMouseEvents.DOWN, evt)}
          onMouseUp={(evt) => onCanvasMouse(CanvasMouseEvents.UP, evt)}
          onMouseOut={(evt) => onCanvasMouse(CanvasMouseEvents.OUT, evt)} />
  );
  return (
    <div className="">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="grid grid-cols-4 justify-center bg-white border border-gray-200 my-2 rounded-lg text-gray-900 max-w-fit mx-auto text-center">
            <li className={buttonStyle + (page === 1 ? " bg-gray-300 hover:bg-gray-200" : "")}>
              <button disabled={page === 1} onClick={() => setPage(page - 1)}>
                Previous Page
              </button>
            </li>
            <li className={buttonStyle}>
              <button disabled={page === pdfDocument!.numPages} onClick={() => setPage(page + 1)}>
                Next Page
              </button>
            </li>
            <li className={buttonStyle}>
              <button onClick={() => increaseZoom()}>
                Zoom +
              </button>
            </li>
            <li className={buttonStyle}>
              <button onClick={() => decreaseZoom()}>
                Zoom -
              </button>
            </li>
          </ul>
        </nav>
      )}
      { smallCanvas && (
        <div className="w-full overflow-scroll mx-auto p-5 border-black border-2">
          { canvasElem }
        </div>
      )}
      { !smallCanvas && (
        <div className="w-full max-h-[75vh] max-w-[75vw] overflow-scroll mx-auto p-5 border-black border-2">
          { canvasElem }
        </div>
      )}
    </div>
  )
}

export default function PdfView({
  pdfSummary,
  smallCanvas,
}: {
  pdfSummary: CompletePdfSummary;
  smallCanvas: boolean;
}) {
  const supabase = useSupabaseClient<Database>();
  // TODO: useSWR instead of state, show loading icon for isLoading
  const { data: pdfData, error, isLoading } = useSWR(
    `storage/${pdfSummary.pdfId}.pdf`,
    () => DataAccessor.instance.getPdfBytes({
      supabase,
      pdfId: pdfSummary.pdfId,
    }),
    {
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  )
  if (pdfData) {
    return (
      <PdfViewer pdfData={pdfData} smallCanvas={smallCanvas} />
    );
  }
  else if (isLoading) {
    return (
      <div className="my-4">
        <div role="status">
        <svg aria-hidden="true" className="w-10 h-10 my-4 mx-auto text-gray-200 animate-spin fill-blue-600" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
          <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>
        </svg><span className="sr-only">Loading...</span>
        </div>
        <span>Downloading { pdfSummary.pdfName }</span>
      </div>
    );
  }
  else {
    return (
      <div className="my-4 text-center space-y-2">
        <div>
          <span>An error occurred downloading the pdf</span>
        </div>
        <div>
          <span>{ pdfSummary.pdfName }</span>
        </div>
        <div>
          <span>{ pdfSummary.pdfId }</span>
        </div>
        <div>
          <span>{ error && JSON.stringify(error, null, 4) }</span>
        </div>
      </div>
    )
  }
}