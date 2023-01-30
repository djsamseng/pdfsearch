

import React, { useEffect, useRef, useState } from "react";

import { usePdf } from "../utils/UsePdf";
import { LoadingSpinner } from "./LoadingSpinner";
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

function calculateBoundingBbox({
  bboxes,
}: {
  bboxes: [number, number, number, number][]
}) {
  if (bboxes.length === 0) {
    return [0, 0, 0, 0];
  }
  let [xMin, yMin, xMax, yMax] = bboxes[0];
  for (const [x0, y0, x1, y1] of bboxes) {
    xMin = Math.min(xMin, x0);
    yMin = Math.min(yMin, y0);
    xMax = Math.max(xMax, x1);
    yMax = Math.max(yMax, y1);
  }
  return [xMin, yMin, xMax, yMax];
}

function scrollAndZoomToBbox({
  bboxes,
  pdfSize,
  imageRef,
  drawCanvasRef,
  setImageWidth,

}: {
  bboxes: [number, number, number, number][] | null;
  pdfSize: {
    pdfWidth: number;
    pdfHeight: number;
  } | null;
  imageRef: React.RefObject<HTMLImageElement>;
  drawCanvasRef: React.RefObject<HTMLCanvasElement>;
  setImageWidth: React.Dispatch<React.SetStateAction<number>>;
}) {
  if (drawCanvasRef.current && drawCanvasRef.current.parentElement) {
    const drawCanvasCtx = drawCanvasRef.current.getContext("2d");
    if (drawCanvasCtx) {
      const parentRect = drawCanvasRef.current.parentElement.getBoundingClientRect();
      drawCanvasCtx.clearRect(0, 0, parentRect.width, parentRect.height);
    }
  }

  if (!bboxes || bboxes.length === 0 || !pdfSize || !imageRef.current || !imageRef.current.parentElement) {
    return;
  }

  const parentRect = imageRef.current.parentElement.getBoundingClientRect();
  const {
    pdfWidth,
    pdfHeight
  } = pdfSize;

  // Calculate desired size
  const bbox = calculateBoundingBbox({ bboxes });
  const bboxWidth = bbox[2] - bbox[0];
  const bboxHeight = bbox[3] - bbox[1];
  // make image width so big that bboxWidth becomes parentRect.width - margin * 2
  const scaleMult = (parentRect.width) / bboxWidth;
  const desiredWidth = Math.min(pdfWidth * 5, Math.round(pdfWidth * scaleMult));
  setImageWidth(desiredWidth);

  // Calculate scroll position: TODO based off of desired width not current width
  const desiredHeight = pdfHeight * desiredWidth / pdfWidth
  const {
    x: topLeftX,
    y: topLeftY,
  } = translatePointToCanvas({
    x: bbox[0],
    y: bbox[3],
    htmlWidth: desiredWidth,
    htmlHeight: desiredHeight,
    pdfWidth,
    pdfHeight,
  });
  const margin = 0;
  if (drawCanvasRef.current) {
    drawCanvasRef.current.width = parentRect.width;
    drawCanvasRef.current.height = parentRect.height;
  }

  setTimeout(() => {
    if (!imageRef.current || !imageRef.current.parentElement) {
      return;
    }
    const scrollLeft = Math.max(topLeftX - margin, 0);
    const scrollTop = Math.max(topLeftY - margin, 0);
    imageRef.current.parentElement.scrollLeft = scrollLeft;
    imageRef.current.parentElement.scrollTop = scrollTop;

    if (!drawCanvasRef.current || !drawCanvasRef.current.parentElement) {
      return;
    }
    const ctx = drawCanvasRef.current.getContext("2d");
    if (!ctx) {
      return;
    }

    for (const elemBbox of bboxes) {
      const x0 = elemBbox[0] * (desiredWidth / pdfWidth) - scrollLeft;
      const y0 = (pdfHeight - elemBbox[3]) * (desiredHeight / pdfHeight) - scrollTop;
      const x1 =  elemBbox[2] * (desiredWidth / pdfWidth) - scrollLeft;
      const y1 = (pdfHeight - elemBbox[1]) * (desiredHeight / pdfHeight) - scrollTop;
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y0);
      ctx.lineTo(x1, y1);
      ctx.lineTo(x0, y1);
      ctx.lineTo(x0, y0);
      ctx.strokeStyle = "blue";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.closePath();
    }
  }, 100);
}

function HeightAdjuster() {
  const [ height, setHeight ] = React.useState(document.body.offsetHeight - window.screen.height);
  useEffect(() => {
    const observer = new ResizeObserver(() => {
      const newHeight = Math.min(20000, document.body.offsetHeight - window.screen.height);
      setHeight(newHeight);
    });
    observer.observe(document.body);
    return () => {
      observer.disconnect();
    }
  });
  return (
    <div style={{height,}}></div>
  );
}

export function PdfImageView({
  pdfData,
}: {
  pdfData: ArrayBuffer;
}) {
  const pdfCanvasRef = useRef<HTMLCanvasElement>(null);
  const drawCanvasRef = useRef<HTMLCanvasElement>(null);
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
    bboxes,
    setBboxes,
  } = React.useContext(PdfViewContext);
  const flag = useRef(false);
  const { pdfDocument, pdfPage } = usePdf({
    pdfData,
    page,
    canvasRef: pdfCanvasRef,
    scale: 1.5,
    onPageRenderSuccess: async (pageObj) => {
      // Cached and thus won't rerender if not needed
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
      if (bboxes === null) {
        if (imageParentRef.current) {
          const parentRect = imageParentRef.current.getBoundingClientRect();
          setImageWidth(parentRect.width);
        }
      }
      setImageDataUrl(pdfImageDataUrl);
    },
    onPageRenderStart: () => {
      // Show loading dialog
      setImageDataUrl(null);
    },
    onPageRenderFail: () => {
      console.error("Page render fail:", page);
    }
  });


  function increaseZoom() {
    setBboxes(null);
    // TODO: move scrollTop and scrollLeft down and right
    setImageWidth(Math.round(imageWidth * 1.1));
  }
  function decreaseZoom() {
    setBboxes(null);
    // TODO: move scrollTop and scrollLeft up and left
    setImageWidth(Math.round(imageWidth * 0.9));
  }
  function nextPage() {
    setPage(page + 1);
    setBboxes(null);
  }
  function prevPage() {
    setPage(page - 1);
    setBboxes(null);
  }
  function onImageMouse(name: CanvasMouseEvents, evt: React.MouseEvent) {
    const imageElem = imageRef.current as HTMLCanvasElement | null;
    if (!imageElem) {
      return;
    }
    if (!imageElem.parentElement) {
      return;
    }
    if (name === CanvasMouseEvents.MOVE) {
      if (evt.buttons) {
        {
          imageElem.parentElement.scrollTop -= evt.movementY;
          imageElem.parentElement.scrollLeft -= evt.movementX;
        }
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
    evt.preventDefault();
  }
  function onCanvasMouse(name: CanvasMouseEvents, evt: React.MouseEvent) {
    const imageElem = imageRef.current as HTMLCanvasElement | null;
    if (!imageElem) {
      return;
    }
    if (!imageElem.parentElement) {
      return;
    }
    if (name === CanvasMouseEvents.MOVE) {
      if (evt.buttons) {
        // TODO: redraw
        setBboxes(null);
        {
          imageElem.parentElement.scrollTop -= evt.movementY;
          imageElem.parentElement.scrollLeft -= evt.movementX;
        }
      }
    }
  }
  useEffect(() => {
    scrollAndZoomToBbox({
      bboxes,
      pdfSize,
      imageRef,
      drawCanvasRef,
      setImageWidth,
    });
  }, [bboxes, page, pdfSize, imageRef, setImageWidth]);
  const buttonStyle = "rounded rounded-none first:rounded-l last:rounded-r border-r last:border-r-0 hover:bg-gray-200 first:hover:bg-gray-300";
  return (
    <div className="flex flex-col">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="grid grid-cols-4 justify-center bg-white border border-gray-200 my-2 rounded-lg text-gray-900 max-w-fit mx-auto text-center">
            <li className={buttonStyle + (page === 1 ? " bg-gray-300 hover:bg-gray-200" : "")} >
              <button disabled={page === 1} className="px-2 py-2" onClick={prevPage}>
                Previous Page
              </button>
            </li>
            <li className={buttonStyle}>
              <button disabled={page === pdfDocument!.numPages} className="px-2 py-2" onClick={nextPage}>
                Next Page
              </button>
            </li>
            <li className={buttonStyle}>
              <button className="px-2 py-2" onClick={increaseZoom}>
                Zoom +
              </button>
            </li>
            <li className={buttonStyle}>
              <button className="px-2 py-2" onClick={decreaseZoom}>
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
          <LoadingSpinner text={`Rendering page ${page}`} />
        </div>
      )}
      <div className="relative">
        <div className="sticky top-[5vh]">
          <div ref={imageParentRef} className="max-h-[90vh] overflow-scroll border">
            { imageDataUrl && (
                <img ref={imageRef} src={imageDataUrl} style={{minWidth: imageWidth, maxWidth: imageWidth}}
                  onMouseMove={(evt) => onImageMouse(CanvasMouseEvents.MOVE, evt)}
                  onMouseDown={(evt) => onImageMouse(CanvasMouseEvents.DOWN, evt)}
                  onMouseUp={(evt) => onImageMouse(CanvasMouseEvents.UP, evt)}
                  onMouseOut={(evt) => onImageMouse(CanvasMouseEvents.OUT, evt)} />
            )}
          </div>
          <div className="absolute top-0 z-10 w-full">
            <div className="max-h-[90vh]">
              <canvas ref={drawCanvasRef}
                onMouseMove={(evt) => onCanvasMouse(CanvasMouseEvents.MOVE, evt)}
                onMouseDown={(evt) => onCanvasMouse(CanvasMouseEvents.DOWN, evt)}
                onMouseUp={(evt) => onCanvasMouse(CanvasMouseEvents.UP, evt)}
                onMouseOut={(evt) => onCanvasMouse(CanvasMouseEvents.OUT, evt)} />
            </div>
          </div>
        </div>

        <HeightAdjuster />
      </div>

    </div>
  )
}