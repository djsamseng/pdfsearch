
import React, { useRef, useState, MouseEvent, useEffect } from "react";
import { useSupabaseClient } from "@supabase/auth-helpers-react";
import * as PdfJS  from "pdfjs-dist/build/pdf"
import useSWR from "swr";

import { DataAccessor } from "../utils/DataAccessor";
import { usePdf } from "../utils/UsePdf";
import { Database } from "../utils/database.types";
import { CompletePdfSummary } from "../utils/requestresponsetypes";
import { PdfViewContext } from "./PdfViewContext";

enum CanvasMouseEvents {
  MOVE = "MOVE",
  DOWN = "DOWN",
  UP = "UP",
  OUT = "OUT",
}

function translatePointToCanvas({
  x,
  y,
  canvasWidth,
  canvasHeight,
  pdfWidth,
  pdfHeight,
}: {
  x: number;
  y: number;
  canvasWidth: number;
  canvasHeight: number;
  pdfWidth: number;
  pdfHeight: number;
}) {
  return [x * canvasWidth / pdfWidth, (pdfHeight - y) * canvasHeight / pdfHeight];
}

function calculateScale({
  canvasRef,
  zoom,
  bbox,
  pdfSize,
}: {
  canvasRef: React.MutableRefObject<null>;
  zoom: number | null;
  bbox: [number, number, number, number] | null;
  pdfSize: {
    width: number;
    height: number;
  } | null;
}) {
  if (zoom !== null) {
    return zoom;
  }
  const defaultValue = 0.4;
  if (bbox === null) {
    return defaultValue;
  }
  if (pdfSize === null) {
    return defaultValue;
  }
  const canvas = canvasRef.current as HTMLCanvasElement | null;
  if (!canvas) {
    return defaultValue;
  }
  if (!canvas.parentElement) {
    return defaultValue;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return defaultValue;
  }

  const canvasRect = canvas.getBoundingClientRect();
  const parentRect = canvas.parentElement.getBoundingClientRect();
  const bboxWidth = bbox[2] - bbox[0];
  const bboxHeight = bbox[3] - bbox[1];
  const desiredWidthRatio = 0.1 * parentRect.width / bboxWidth;
  const desiredHeightRatio = 0.1 * parentRect.height / bboxHeight;

  const [topLeftX, topLeftY] = translatePointToCanvas({
    x: bbox[0],
    y: bbox[3],
    canvasWidth: canvasRect.width,
    canvasHeight: canvasRect.height,
    pdfWidth: pdfSize.width,
    pdfHeight: pdfSize.height,
  });
  canvas.parentElement.scrollLeft = Math.max(topLeftX - bboxWidth, 0);
  canvas.parentElement.scrollTop = Math.max(topLeftY - bboxHeight, 0);
  const desiredScale = Math.max(desiredWidthRatio, desiredHeightRatio);



  // Rendering is too slow - instead use canvasContext.getImageData(bbox[0], pdfHeight-bbox[1], width, height)
  // and scale up the image
  return Math.min(desiredScale, 1.5);
}

function PdfViewer({
  pdfData,
  smallCanvas,
}: {
  pdfData: ArrayBuffer;
  smallCanvas: boolean;
}) {
  const canvasRef = useRef(null);
  const {
    page,
    setPage,
    bbox,
    setBbox,
    zoom,
    setZoom,
    pdfSize,
    setPdfSize,
  } = React.useContext(PdfViewContext);
  const scale = calculateScale({
    canvasRef,
    zoom,
    bbox,
    pdfSize,
  });
  console.log("scale:", scale);
  const flag = useRef(false);


  function drawBbox({
    pdfWidth,
    pdfHeight,
  }: {
    pdfWidth: number;
    pdfHeight: number;
  }) {
    if (bbox === null) {
      console.log("Bbox null");
      return;
    }
    const canvas = canvasRef.current as HTMLCanvasElement | null;
    if (!canvas) {
      console.log("No canvas");
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      console.log("No ctx");
      return;
    }
    const canvasRect = canvas.getBoundingClientRect();
    const [topLeftX, topLeftY] = translatePointToCanvas({
      x: bbox[0],
      y: bbox[3],
      canvasWidth: canvasRect.width,
      canvasHeight: canvasRect.height,
      pdfWidth,
      pdfHeight,
    });
    const [bottomRightX, bottomRightY] = translatePointToCanvas({
      x: bbox[2],
      y: bbox[1],
      canvasWidth: canvasRect.width,
      canvasHeight: canvasRect.height,
      pdfWidth,
      pdfHeight,
    });
    ctx.beginPath();
    ctx.moveTo(topLeftX, topLeftY);
    ctx.lineTo(topLeftX, bottomRightY);
    ctx.lineTo(bottomRightX, bottomRightY);
    ctx.lineTo(bottomRightX, topLeftY);
    ctx.lineTo(topLeftX, topLeftY);
    ctx.strokeStyle = "blue";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.closePath();
  }
  const { pdfDocument, pdfPage } = usePdf({
    pdfData,
    page,
    canvasRef,
    scale,
    onPageRenderSuccess: async (page) => {
      console.log("Rendered pdf", page.view, page);
      const [y0, x0, y1, x1] = page.view;
      const pdfWidth = x1 - x0;
      const pdfHeight = y1 - y0;
      setPdfSize({
        width: pdfWidth,
        height: pdfHeight,
      })
    },
  });

  // TODO: Clear other drawings
  React.useEffect(() => {
    if (pdfSize !== null) {
      drawBbox({
        pdfWidth: pdfSize.width,
        pdfHeight: pdfSize.height,
      });
    }
  }, [bbox])

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
    <div className="flex flex-col">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="grid grid-cols-4 justify-center bg-white border border-gray-200 my-2 rounded-lg text-gray-900 max-w-fit mx-auto text-center">
            <li className={buttonStyle + (page === 1 ? " bg-gray-300 hover:bg-gray-200" : "")}>
              <button disabled={page === 1} onClick={() => {
                setPage(page - 1);
                setBbox(null);
              }}>
                Previous Page
              </button>
            </li>
            <li className={buttonStyle}>
              <button disabled={page === pdfDocument!.numPages} onClick={() => {
                setPage(page + 1);
                setBbox(null);
              }}>
                Next Page
              </button>
            </li>
            <li className={buttonStyle}>
              <button onClick={() => setZoom(scale * 1.1)}>
                Zoom +
              </button>
            </li>
            <li className={buttonStyle}>
              <button onClick={() => setZoom(scale * 0.9)}>
                Zoom -
              </button>
            </li>
          </ul>
        </nav>
      )}
      { smallCanvas && (
        <div className="max-h-screen overflow-scroll p-5 border-black border-2">
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
      <PdfViewer pdfData={pdfData}
        smallCanvas={smallCanvas} />
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