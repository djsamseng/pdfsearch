import { PdfElements } from "../utils/sharedtypes";
import PdfElementsDrawer from "./pdfelementsdrawer";


export default function PdfSelected(props: {
  elems: PdfElements,
}) {
  return (
    <div>
      <PdfElementsDrawer elems={props.elems} />
    </div>
  )
}