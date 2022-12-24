
import { ChangeEvent, MouseEventHandler, MouseEvent, useRef, useState } from "react";
import { usePdf } from "@mikecousins/react-pdf";

enum CanvasMouseEvents {
  MOVE = "MOVE",
  DOWN = "DOWN",
  UP = "UP",
  OUT = "OUT",
}

function PdfMaker(props: { pdfDocumentUrl: string }) {
  const canvasRef = useRef(null);
  const [ page, setPage ] = useState(1);
  const [ scale, setScale ] = useState(0.4);
  const [ drawMode, setDrawMode ] = useState(false);
  const prevX = useRef(0);
  const prevY = useRef(0);
  const currX = useRef(0);
  const currY = useRef(0);
  const flag = useRef(false);
  const { pdfDocument, pdfPage } = usePdf({
    file: props.pdfDocumentUrl,
    page,
    canvasRef,
    scale: scale,
  });

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
    const canvasX = evt.clientX - parentRect.left;
    const canvasY = evt.clientY - parentRect.top;
    if (name === CanvasMouseEvents.MOVE) {
      if (evt.buttons) {
        if (drawMode) {
          if (flag.current) {
            prevX.current = currX.current;
            prevY.current = currY.current;
            currX.current = canvasX;
            currY.current = canvasY;
            draw();
          }
        }
        else {
          canvas.parentElement.scrollTop -= evt.movementY;
          canvas.parentElement.scrollLeft -= evt.movementX;
        }
      }
    }
    else if (name === CanvasMouseEvents.DOWN) {
      if (drawMode) {
        prevX.current = currX.current;
        prevY.current = currY.current;
        currX.current = canvasX;
        currY.current = canvasY;
        flag.current = true;
      }
    }
    else if (name === CanvasMouseEvents.UP) {
      flag.current = false;
    }
    else if (name === CanvasMouseEvents.OUT) {
      flag.current = false;
    }

  }
  function draw() {
    const canvas = canvasRef.current as HTMLCanvasElement | null;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    ctx.beginPath();
    ctx.moveTo(prevX.current, prevY.current);
    ctx.lineTo(currX.current, currY.current);
    ctx.strokeStyle = "black";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.closePath();
  }
  const buttonStyle = "rounded px-2 py-1";
  const buttonStyleActive = "bg-blue-100 border-2 rounded px-2 py-1"
  return (
    <div className="">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="flex justify-center">
            <li className="previous">
              <button disabled={page === 1} onClick={() => setPage(page + 1)} className={buttonStyle}>
                Previous
              </button>
            </li>
            <li className="next">
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
            <li>
              <button onClick={() => setDrawMode(false)} className={ !drawMode ? buttonStyleActive : buttonStyle}>
                Drag
              </button>
            </li>
            <li>
              <button onClick={() => setDrawMode(true)} className={ drawMode ? buttonStyleActive : buttonStyle}>
                Draw
              </button>
            </li>
          </ul>
        </nav>
      )}
      <div className="h-[50vh] w-[50vw] overflow-x-scroll mx-auto p-5 border-black border-2">
        <canvas ref={canvasRef} className={drawMode ? "cursor-crosshair" : "cursor-grab" }
          onMouseMove={(evt) => onCanvasMouse(CanvasMouseEvents.MOVE, evt)}
          onMouseDown={(evt) => onCanvasMouse(CanvasMouseEvents.DOWN, evt)}
          onMouseUp={(evt) => onCanvasMouse(CanvasMouseEvents.UP, evt)}
          onMouseOut={(evt) => onCanvasMouse(CanvasMouseEvents.OUT, evt)} />
      </div>
    </div>
  )
}

export default function PdfUpload() {
  const [ pdfDocumentUrl, setPdfDocumentUrl ] = useState<string | undefined>(undefined);
  const canvasRef = useRef(null);
  function onPdfFileChange(evt: ChangeEvent<HTMLInputElement>) {
    const fileObj = evt.target.files && evt.target.files[0];
    console.log(fileObj);
    if (!fileObj) {
      return;
    }
    const url = URL.createObjectURL(fileObj);
    setPdfDocumentUrl(url);
  }

  return (
    <div className="w-full text-center">
      <input type="file" accept=".pdf" onChange={onPdfFileChange} />
      { pdfDocumentUrl && (
        <PdfMaker pdfDocumentUrl={pdfDocumentUrl} />
      )}
    </div>
  )
}