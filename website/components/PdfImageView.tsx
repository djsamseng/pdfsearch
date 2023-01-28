

import React, { useRef, useState } from "react";

import { usePdf } from "../utils/UsePdf";
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

export function PdfImageView({
  pdfData,
}: {
  pdfData: ArrayBuffer;
}) {
  console.log("HERE!");
  const canvasRef = useRef(null);
  const [ imageDataUrl, setImageDataUrl ] = useState<string | null>(null);
  const [ imageWidth, setImageWidth ] = useState<number>(3000);
  const {
    page,
    setPage,
    bbox,
    setBbox,
    //zoom,
    //setZoom,
    //pdfSize,
    //setPdfSize,
  } = React.useContext(PdfViewContext);
  const flag = useRef(false);
  const { pdfDocument, pdfPage } = usePdf({
    pdfData,
    page,
    canvasRef,
    scale: 1.5,
    onPageRenderSuccess: async (page) => {
      console.log("Rendered pdf", page.view, page);
      const canvas = canvasRef.current as HTMLCanvasElement | null;
      if (!canvas) {
        console.log("No canvas");
        return;
      }
      const pdfImageDataUrl = canvas.toDataURL("image/png");
      setImageDataUrl(pdfImageDataUrl);
    },
  });
  function increaseZoom() {
    setImageWidth(Math.round(imageWidth * 1.1));
  }
  function decreaseZoom() {
    setImageWidth(Math.round(imageWidth * 0.9));
  }
  const buttonStyle = "rounded px-2 py-2 rounded-none first:rounded-l last:rounded-r border-r last:border-r-0 hover:bg-gray-200 first:hover:bg-gray-300";
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
              <button onClick={increaseZoom}>
                Zoom +
              </button>
            </li>
            <li className={buttonStyle}>
              <button onClick={decreaseZoom}>
                Zoom -
              </button>
            </li>
          </ul>
        </nav>
      )}
      <div className="hidden">
        <canvas ref={canvasRef} />
      </div>
      { imageDataUrl && (
        <div className="max-h-screen overflow-scroll p-5 border-black border-2">
          <img src={imageDataUrl} style={{minWidth: imageWidth, maxWidth: imageWidth,}}/>
        </div>
      )}
    </div>
  )
}