import { useEffect, useRef } from "react";


type PathM = [String, [number, number]];
type PathL = [String, [number, number]];
type PathData = PathM | PathL;

export type PathElement = {
  path: Array<PathData>;
}

type CharElement = {
  x: number;
  y: number;
  char: string;
}

export type PdfElements = Array<PathElement | CharElement >;
export type PdfSelectedObjects = {
  searchPaths: Array<PathElement>;
  pathMinX: number;
  pathMinY: number;
}

export default function PdfElementsDrawer(props: {
  elems: PdfSelectedObjects,
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  function drawPath(ctx: CanvasRenderingContext2D, path: Array<PathData>, pathMinX: number, pathMinY: number) {
    ctx.beginPath();
    for (const point of path) {
      if (point[0] === "m") {
        const x = point[1][0] - pathMinX;
        const y = point[1][1] - pathMinY;
        ctx.moveTo(x, y);
      }
      else if (point[0] === "l") {
        const x = point[1][0] - pathMinX;
        const y = point[1][1] - pathMinY;
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
    const {
      searchPaths,
      pathMinX,
      pathMinY,
    } = props.elems;
    console.log("Got canvas", searchPaths.length);
    for (const elem of searchPaths) {
      if ("path" in elem) {
        const { path } = elem;
        drawPath(ctx, path, pathMinX, pathMinY);
      }
      if ("char" in elem) {
        const { char, x: xOrig, y: yOrig } = elem as unknown as CharElement;
        const x = Math.max(xOrig - pathMinX, 10);
        const y = Math.max(yOrig - pathMinY, 10);
        console.log("Draw text", char, x, y);
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