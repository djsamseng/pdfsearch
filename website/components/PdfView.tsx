
import { useRef, useState, MouseEvent } from "react";
import { usePdf } from "@mikecousins/react-pdf";
import * as PdfJS  from "pdfjs-dist/build/pdf"

import { ClientDrawPath } from "../utils/sharedtypes";

enum CanvasMouseEvents {
  MOVE = "MOVE",
  DOWN = "DOWN",
  UP = "UP",
  OUT = "OUT",
}

export default function PdfView() {
  // TODO: https://github.com/mozilla/pdf.js/blob/master/examples/learning/helloworld64.html#L42
  // And replace https://github.com/mikecousins/react-pdf-js/blob/9b0be61ea478042727f11328ca1b27ecd8b4e411/packages/react-pdf-js/src/index.tsx#L92
  const canvasRef = useRef(null)
  const [ page, setPage ] = useState(1);
  const [ scale, setScale ] = useState(0.4);
  const flag = useRef(false);

  const pdfDocument: any = null;
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

  const buttonStyle = "rounded px-2 py-1";
  const buttonStyleActive = "bg-blue-100 border-2 rounded px-2 py-1";
  return (
    <div className="">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="flex justify-center">
            <li>
              <button disabled={page === 1} onClick={() => setPage(page - 1)} className={buttonStyle}>
                Previous
              </button>
            </li>
            <li>
              <button disabled={page === pdfDocument!.numPages} onClick={() => setPage(page + 1)} className={buttonStyle}>
                Next
              </button>
            </li>
            <li>
              <button onClick={() => increaseZoom()} className={buttonStyle}>
                Zoom +
              </button>
            </li>
            <li>
              <button onClick={() => decreaseZoom()} className={buttonStyle}>
                Zoom -
              </button>
            </li>
          </ul>
        </nav>
      )}
      <div className="h-[75vh] w-[75vw] overflow-scroll mx-auto p-5 border-black border-2">
        <canvas ref={canvasRef} className={"cursor-grab" }
          onMouseMove={(evt) => onCanvasMouse(CanvasMouseEvents.MOVE, evt)}
          onMouseDown={(evt) => onCanvasMouse(CanvasMouseEvents.DOWN, evt)}
          onMouseUp={(evt) => onCanvasMouse(CanvasMouseEvents.UP, evt)}
          onMouseOut={(evt) => onCanvasMouse(CanvasMouseEvents.OUT, evt)} />
      </div>
    </div>
  )
}