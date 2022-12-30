

// Client side generated
export type ClientDrawPath = {
  currX: number;
  currY: number;
  prevX: number;
  prevY: number;
}

// Server side generated
type PdfPathM = [String, [number, number]];
type PdfPathL = [String, [number, number]];
export type PdfPathData = PdfPathM | PdfPathL;

export type PdfPathElement = {
  path: Array<PdfPathData>;
  bbox: [number, number, number, number];
}

export type PdfCharElement = {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  char: string;
  bbox: [number, number, number, number];
}

export type PdfElements = Array<PdfPathElement | PdfCharElement>;
