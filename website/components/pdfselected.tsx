import PdfElementsDrawer, { PdfSelectedObjects } from "./pdfelementsdrawer";


export default function PdfSelected(props: {
  elems: PdfSelectedObjects,
}) {
  return (
    <div>
      <PdfElementsDrawer elems={props.elems} />
    </div>
  )
}