

import { useState } from "react";
import { CompletePdfSummary, PdfJsonResponse } from "../utils/requestresponsetypes";

function Accordion({
  id,
  isFirst,
  isLast,
  item,
}: {
  id: string;
  isFirst: boolean;
  isLast: boolean;
  item: {
    heading: React.ReactNode;
    body: React.ReactNode;
  };
}) {
  const [ isOpen, setIsOpen ] = useState(false);
  const chevronDown = (
    <svg data-accordion-icon className="w-6 h-6 shrink-0" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"></path>
    </svg>
  )
  const chevronUp = (
    <svg data-accordion-icon className="w-6 h-6 rotate-180 shrink-0" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"></path>
    </svg>
  )
  return (
    <div key={id}>
      <div>
        <button
          type="button"
          className={`flex items-center justify-between w-full p-5 font-medium text-left text-gray-500 border ${!isLast ? "border-b-0" : ""} border-gray-200 ${isFirst ? "rounded-t-xl" : ""} focus:ring-4 focus:ring-gray-200`}
          aria-expanded={isOpen}
          aria-controls={`accordion-open-body-${id}`}
          onClick={() => setIsOpen(!isOpen)}>
          <div className="flex-grow grid grid-cols-3 gap-2">
            {item.heading}
          </div>
          { isOpen ? chevronUp : chevronDown }
        </button>
      </div>
      <div id={`accordion-open-body-${id}`} className={isOpen ? "" : "hidden"} aria-labelledby="accordion-open-heading-1">
        <div className={`p-5 font-light border ${isLast ? "" : "border-b-0"} border-gray-200`}>
          {item.body}
        </div>
      </div>
    </div>
  )
}

function NestedAccordion({
  elems,
}: {
  elems: Record<string, Record<string, PdfJsonResponse[]>> | Record<string, PdfJsonResponse[]>;
}) {
  const keys = Object.keys(elems);
  elems
  return (
    <>
      { keys.map((key, idx) => {
        const item = elems[key];
        const itemKeys = Object.keys(item);
        let body;
        if (Array.isArray(item)) {
          body = (
            <div>
              { JSON.stringify(item) }
            </div>
          )
        }
        else {
          body = (
            <NestedAccordion elems={item} />
          )
        }
        return (
          <Accordion item={{
            heading: key,
            body,
          }} id={key} isFirst={idx === 0} isLast={idx === keys.length - 1} />
        )
      })}
    </>
  )
}

function merge2(out: Record<string, PdfJsonResponse[]>, newItems: Record<string, PdfJsonResponse[]>) {
  Object.entries(newItems).forEach(([key, item]) => {
    for (const subitem of Object.values(item)) {
      if (!(key in out)) {
        out[key] = [];
      }
      out[key].push({
        label: subitem.label,
        bbox: [...subitem.bbox],
      });
    }
  });
}

function mergeRecordItems(items: Record<string, Record<string, Record<string, PdfJsonResponse[]>>>) {
  return Object.entries(items).reduce((out, [_, item]) => {
    // Drop the top key
    for (const subkey of Object.keys(item)) {
      out[subkey] = {}
    }

    Object.entries(item).forEach(([subkey, subitem]) => {
      merge2(out[subkey], subitem);
    });
    return out;
  }, {} as Record<string, Record<string, PdfJsonResponse[]>>);
}

export default function SummaryElementList({
  pdfSummary,
}: {
  pdfSummary: CompletePdfSummary;
}) {
  const {
    doors,
    windows,
  } = pdfSummary.pdfSummary;
  const doorsAllPages = mergeRecordItems(doors);
  const windowsAllPages = mergeRecordItems(windows);
  const items = [{
    id: "Doors",
    heading: (
      <>
        <div className="overflow-clip">Doors</div>
        <div className="overflow-clip">10</div>
        <div className="overflow-clip">Page 3,4,5</div>
      </>
    ),
    body: (
      <NestedAccordion elems={doorsAllPages} />
    )
  }, {
    id: "Windows",
    heading: (
      <>
        <div className="overflow-clip">Windows</div>
        <div className="overflow-clip">30</div>
        <div className="overflow-clip">Page 3,4,5</div>
      </>
    ),
    body: (
      <NestedAccordion elems={windowsAllPages} />
    )
  }];
  return (
    <div className="m-4">
      { items.map((item, idx) => {
        return (
          <Accordion item={item} id={item.id} isFirst={idx === 0} isLast={idx === items.length - 1}  />
        );
      })}
    </div>
  )
}