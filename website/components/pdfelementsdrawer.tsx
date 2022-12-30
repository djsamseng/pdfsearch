import { useEffect, useRef } from "react";

import { PdfElements, PdfPathData, } from "../utils/sharedtypes";

export default function PdfElementsDrawer(props: {
  elems: PdfElements,
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  function drawPath(ctx: CanvasRenderingContext2D, path: Array<PdfPathData>) {
    ctx.beginPath();
    for (const point of path) {
      if (point[0] === "m") {
        const x = point[1][0];
        const y = point[1][1];
        ctx.moveTo(x, y);
      }
      else if (point[0] === "l") {
        const x = point[1][0];
        const y = point[1][1];
        ctx.lineTo(x, y);
      }
    }
    ctx.strokeStyle = "black";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.closePath();
  }
  function drawElems() {
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
    console.log(props.elems);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    console.log("Got canvas", props.elems.length);
    for (const elem of props.elems) {
      if ("path" in elem) {
        const { path } = elem;
        drawPath(ctx, path);
      }
      if ("char" in elem) {
        const { char, x: xOrig, y: yOrig } = elem;
        const x = Math.max(xOrig, 10);
        const y = Math.max(yOrig, 10);
        ctx.font = "12px serif";
        ctx.fillText(char, x, y);
      }
    }
  }
  useEffect(() => {
    drawElems();
  }, [props.elems]);

  return (
    <div className="h-[50vh] w-[50vw] overflow-scroll mx-auto p-5 mt-2 border-black border-2">
      <canvas ref={canvasRef} />
    </div>
  )
}