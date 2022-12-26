
import { ChangeEvent, MouseEventHandler, MouseEvent, MutableRefObject, useRef, useState, useEffect, createContext } from "react";
import { usePdf } from "@mikecousins/react-pdf";
import { PDFDocumentProxy } from "pdfjs-dist";

enum CanvasMouseEvents {
  MOVE = "MOVE",
  DOWN = "DOWN",
  UP = "UP",
  OUT = "OUT",
}

type DrawPath = {
  currX: number;
  currY: number;
  prevX: number;
  prevY: number;
}

function PdfMaker2(props: { pdfDocumentUrl: string }) {
  const canvasRef = useRef(null);
  const [ page, setPage ] = useState(1);
  const [ scale, setScale ] = useState(0.4);
  const drawMode = useRef(false);
  const { pdfDocument, pdfPage } = usePdf({
    file: props.pdfDocumentUrl,
    page,
    canvasRef,
    scale: scale,
  });
  function setDrawMode(val: boolean) {
    const canvas = canvasRef.current as HTMLCanvasElement | null;
    if (!canvas) {
      return;
    }
    canvas.style.cursor = val ? "crosshair" : "grab";
  }
  const buttonStyle = "rounded px-2 py-1";
  const buttonStyleActive = "bg-blue-100 border-2 rounded px-2 py-1"
  return (
    <div className="">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="flex justify-center">
            <li>
              <button disabled={page === 1} onClick={() => setPage(page + 1)} className={buttonStyle}>
                Previous
              </button>
            </li>
            <li>
              <button disabled={page === pdfDocument!.numPages} onClick={() => setPage(page + 1)} className={buttonStyle}>
                Next
              </button>
            </li>
            <li>
              <button onClick={() => setDrawMode(false)} className={ !drawMode.current ? buttonStyleActive : buttonStyle}>
                Drag
              </button>
            </li>
            <li>
              <button onClick={() => setDrawMode(true)} className={ drawMode.current ? buttonStyleActive : buttonStyle}>
                Draw
              </button>
            </li>
          </ul>
        </nav>
      )}
      <div className="h-[50vh] w-[50vw] overflow-scroll mx-auto p-5 border-black border-2">
        <canvas ref={canvasRef} className={drawMode.current ? "cursor-crosshair" : "cursor-grab" }/>
      </div>
    </div>
  )
}

const DrawModeContext = createContext(false);
// State in parent, owns canvasRef
// Pdf in one child, creates canvas with props.canvasRef
// Button control in another child with prop setter and getter
// parentSetter sets new prop on button control and calls canvas.style.cursor = val ? "crosshair" : "grab";

function DrawModeControl(props: { drawMode: boolean; setDrawMode: (val:boolean)=>void }) {
  const buttonStyle = "rounded px-2 py-1";
  const buttonStyleActive = "bg-blue-100 border-2 rounded px-2 py-1"
  return (
    <div>
      <li>
        <button onClick={() => props.setDrawMode(false)} className={ !props.drawMode ? buttonStyleActive : buttonStyle}>
          Drag
        </button>
      </li>
      <li>
        <button onClick={() => props.setDrawMode(true)} className={ props.drawMode ? buttonStyleActive : buttonStyle}>
          Draw
        </button>
      </li>
    </div>
  )
}

function PdfDrawer(props: { canvasRef: MutableRefObject<null> }) {

}

function PdfMakerParent() {
  const canvasRef = useRef(null);
  const [ drawMode, setDrawModeState ] = useState(false);
  function setDrawMode(val: boolean) {
    const canvas = canvasRef.current as HTMLCanvasElement | null;
    if (!canvas) {
      return;
    }
    canvas.style.cursor = val ? "crosshair" : "grab";
  }
  return (
    <div></div>
  );
}

function PdfMaker(props: { pdfDocumentUrl: string }) {
  const canvasRef = useRef(null);
  const [ page, setPage ] = useState(1);
  const [ scale, setScale ] = useState(0.4);
  // drawMode is state for the button but a ref for the canvas

  const [ drawMode, setDrawMode ] = useState(false);
  // Use refs from drawing so that we don't have to
  // redraw / reparse the pdf the entire pdf every time
  const prevX = useRef(0);
  const prevY = useRef(0);
  const currX = useRef(0);
  const currY = useRef(0);
  const currPdfX = useRef(0);
  const currPdfY = useRef(0);
  const prevPdfX = useRef(0);
  const prevPdfY = useRef(0);
  const flag = useRef(false);
  const drawPaths = useRef<Array<DrawPath>>([]);
  const { pdfDocument, pdfPage } = usePdf({
    file: props.pdfDocumentUrl,
    page,
    canvasRef,
    scale: scale,
  });
  function roll(canvasX: number, canvasY: number, pdfX: number, pdfY: number) {
    prevX.current = currX.current;
    prevY.current = currY.current;
    currX.current = canvasX;
    currY.current = canvasY;

    prevPdfX.current = currPdfX.current;
    prevPdfY.current = currPdfY.current;
    currPdfX.current = pdfX;
    currPdfY.current = pdfY;
  }

  function clearDrawPaths() {
    drawPaths.current = [];
    // Force a rerender
    setScale(scale * 1.00001);
  }
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
    const pdfX = (canvasX + canvas.scrollLeft) / scale;
    const pdfY = (canvasY + canvas.scrollTop) / scale;
    if (name === CanvasMouseEvents.MOVE) {
      if (evt.buttons) {
        if (drawMode) {
          if (flag.current) {
            roll(canvasX, canvasY, pdfX, pdfY);
            drawCurrent();
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
        roll(canvasX, canvasY, pdfX, pdfY);
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
  function drawCurrent() {
    const canvas = canvasRef.current as HTMLCanvasElement | null;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    drawPaths.current.push({
      currX: currPdfX.current,
      currY: currPdfY.current,
      prevX: prevPdfX.current,
      prevY: prevPdfY.current,
    });
    ctx.globalCompositeOperation = "source-over";
    ctx.beginPath();
    ctx.moveTo(prevX.current, prevY.current);
    ctx.lineTo(currX.current, currY.current);
    ctx.strokeStyle = "black";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.closePath();
  }
  function drawFromState() {
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
    ctx.globalCompositeOperation = "destination-over";

    for (const path of drawPaths.current) {
      ctx.beginPath();
      ctx.moveTo(path.prevX * scale, path.prevY * scale);
      ctx.lineTo(path.currX * scale, path.currY * scale);
      ctx.strokeStyle = "black";
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.closePath();
    }
  }
  drawFromState();

  const buttonStyle = "rounded px-2 py-1";
  const buttonStyleActive = "bg-blue-100 border-2 rounded px-2 py-1"
  return (
    <div className="">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="flex justify-center">
            <li>
              <button disabled={page === 1} onClick={() => setPage(page + 1)} className={buttonStyle}>
                Previous
              </button>
            </li>
            <li>
              <button disabled={page === pdfDocument!.numPages} onClick={() => setPage(page + 1)} className={buttonStyle}>
                Next
              </button>
            </li>
            <li>
              <button onClick={() => clearDrawPaths()} className={buttonStyle}>
                Clear
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
      <div className="h-[50vh] w-[50vw] overflow-scroll mx-auto p-5 border-black border-2">
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