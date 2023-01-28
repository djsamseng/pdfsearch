

import React, { useEffect, useRef, useState } from "react";

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
  htmlWidth,
  htmlHeight,
  pdfWidth,
  pdfHeight,
}: {
  x: number;
  y: number;
  htmlWidth: number;
  htmlHeight: number;
  pdfWidth: number;
  pdfHeight: number;
}) {
  return {
    x: x * htmlWidth / pdfWidth,
    y: (pdfHeight - y) * htmlHeight / pdfHeight
  };
}

function scrollAndZoomToBbox({
  bbox,
  pdfSize,
  imageRef,
  setImageWidth,
}: {
  bbox: [number, number, number, number] | null;
  pdfSize: {
    pdfWidth: number;
    pdfHeight: number;
  } | null;
  imageRef: React.RefObject<HTMLImageElement>;
  setImageWidth: React.Dispatch<React.SetStateAction<number>>;
}) {
  if (!bbox || !pdfSize || !imageRef.current || !imageRef.current.parentElement) {
    return;
  }

  const imageRect = imageRef.current.getBoundingClientRect();
  const parentRect = imageRef.current.parentElement.getBoundingClientRect();
  const {
    pdfWidth,
    pdfHeight
  } = pdfSize;
  const {
    x: topLeftX,
    y: topLeftY,
  } = translatePointToCanvas({
    x: bbox[0],
    y: bbox[3],
    htmlWidth: imageRect.width,
    htmlHeight: imageRect.height,
    pdfWidth,
    pdfHeight,
  });
  const margin = 50;
  imageRef.current.parentElement.scrollLeft = Math.max(topLeftX - margin, 0);
  imageRef.current.parentElement.scrollTop = Math.max(topLeftY - margin, 0);

  const bboxWidth = bbox[2] - bbox[0];
  const bboxHeight = bbox[3] - bbox[1];
  // make image width so big that bboxWidth becomes parentRect.width - margin * 2
  const scaleMult = (parentRect.width) / bboxWidth;
  const desiredWidth = Math.min(pdfWidth * 5, Math.round(pdfWidth * scaleMult));
  setImageWidth(desiredWidth);
}

export function PdfImageView({
  pdfData,
}: {
  pdfData: ArrayBuffer;
}) {
  const pdfCanvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const imageParentRef = useRef<HTMLDivElement>(null);
  const [ imageDataUrl, setImageDataUrl ] = useState<string | null>(null);
  const [ imageWidth, setImageWidth ] = useState<number>(300);
  const [ pdfSize, setPdfSize ] = useState<{
    pdfWidth: number;
    pdfHeight: number;
  } | null>(null);
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
    canvasRef: pdfCanvasRef,
    scale: 1.5,
    onPageRenderSuccess: async (pageObj) => {
      // Cached and thus won't rerender if not needed
      // TODO: If toggled back and forth we render the wrong page but think we're on the right page
      console.log("Rendered pdf", pageObj.view, page, bbox);
      const [y0, x0, y1, x1] = pageObj.view;
      const canvas = pdfCanvasRef.current;
      if (!canvas) {
        console.log("No canvas after page rendered");
        return;
      }
      const pdfImageDataUrl = canvas.toDataURL("image/png");

      const pdfWidth = x1 - x0;
      const pdfHeight = y1 - y0;
      setPdfSize({
        pdfWidth: pdfWidth,
        pdfHeight: pdfHeight,
      });
      if (bbox === null) {
        if (imageParentRef.current) {
          const parentRect = imageParentRef.current.getBoundingClientRect();
          setImageWidth(parentRect.width);
        }
      }
      setImageDataUrl(pdfImageDataUrl);
    },
    onPageRenderStart: () => {
      // Show loading dialog
      console.log("Rendering start", page);
      setImageDataUrl(null);
    },
    onPageRenderFail: () => {
      console.log("Page render fail:", page);
    }
  });


  function increaseZoom() {
    setBbox(null);
    setImageWidth(Math.round(imageWidth * 1.1));
  }
  function decreaseZoom() {
    setBbox(null);
    setImageWidth(Math.round(imageWidth * 0.9));
  }
  function nextPage() {
    setPage(page + 1);
    setBbox(null);
  }
  function prevPage() {
    setPage(page - 1);
    setBbox(null);
  }
  useEffect(() => {
    scrollAndZoomToBbox({
      bbox,
      pdfSize,
      imageRef,
      setImageWidth,
    });
  }, [bbox, page, pdfSize, imageRef, setImageWidth]);
  const buttonStyle = "rounded px-2 py-2 rounded-none first:rounded-l last:rounded-r border-r last:border-r-0 hover:bg-gray-200 first:hover:bg-gray-300";
  return (
    <div className="flex flex-col">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="grid grid-cols-4 justify-center bg-white border border-gray-200 my-2 rounded-lg text-gray-900 max-w-fit mx-auto text-center">
            <li className={buttonStyle + (page === 1 ? " bg-gray-300 hover:bg-gray-200" : "")}>
              <button disabled={page === 1} onClick={prevPage}>
                Previous Page
              </button>
            </li>
            <li className={buttonStyle}>
              <button disabled={page === pdfDocument!.numPages} onClick={nextPage}>
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
        <canvas ref={pdfCanvasRef} />
      </div>
      { !imageDataUrl && (
        <div>
          Loading...
        </div>
      )}
      <div className="relative">
        <div className="sticky top-[5vh]">
          <div ref={imageParentRef} className="max-h-[90vh] overflow-scroll p-5">
            { imageDataUrl && (
              <img ref={imageRef} src={imageDataUrl} style={{minWidth: imageWidth, maxWidth: imageWidth,}}/>
            )}
          </div>
        </div>
        <div style={{height: 5000,}}></div>
      </div>

    </div>
  )
}