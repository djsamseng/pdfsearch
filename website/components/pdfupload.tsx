import { ChangeEvent, useRef, useState } from "react";
import { usePdf } from "@mikecousins/react-pdf";

function PdfMaker(props: { pdfDocumentUrl: string }) {
  const canvasRef = useRef(null);
  const [ page, setPage ] = useState(1);
  const [ scale, setScale ] = useState(0.4);
  const { pdfDocument, pdfPage } = usePdf({
    file: props.pdfDocumentUrl,
    page,
    canvasRef,
    scale: scale,
  })
  function increaseZoom() {
    setScale(scale * 1.1);
  }
  function decreaseZoom() {
    setScale(scale * 0.9);
  }
  return (
    <div className="">
      {Boolean(pdfDocument && pdfDocument.numPages > 0) && (
        <nav>
          <ul className="pager">
            <li className="previous">
              <button disabled={page === 1} onClick={() => setPage(page + 1)}>
                Previous
              </button>
            </li>
            <li className="next">
              <button disabled={page === pdfDocument!.numPages} onClick={() => setPage(page + 1)}>
                Next
              </button>
            </li>
            <li>
              <button onClick={() => increaseZoom()}>
                Zoom +
              </button>
            </li>
            <li>
              <button onClick={() => decreaseZoom()}>
                Zoom -
              </button>
            </li>
          </ul>
        </nav>
      )}
      <div className="h-[50vh] w-[50vw] overflow-x-scroll mx-auto ">
        <canvas ref={canvasRef} />
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