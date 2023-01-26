

import { useState } from "react";
import { CompletePdfSummary, PdfJsonResponse, PdfSummaryJson } from "../utils/requestresponsetypes";

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
      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd"></path>
    </svg>
  )
  const chevronUp = (
    <svg data-accordion-icon className="w-6 h-6 rotate-180 shrink-0" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd"></path>
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

function merge2(out: Record<string, PdfJsonResponse[]>, newItems: Record<string, PdfJsonResponse[]>) {
  Object.entries(newItems).forEach(([key, item]) => {
    for (const subitem of Object.values(item)) {
      if (!(key in out)) {
        out[key] = [];
      }
      out[key].push({
        label: subitem.label,
        bbox: [...subitem.bbox],
        page_number: subitem.page_number,
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

function countsForObj(record: Record<string, unknown>) {
  return Object.entries(record).reduce((sum, [key, items]) => {
    if (Array.isArray(items)) {
      sum += items.length;
    }
    else if (typeof items === "object") {
      sum += countsForObj(items as Record<string, unknown>);
    }
    return sum;
  }, 0);
}

type TableViewData = {
  header: string[];
  rows: Array<{
    row: string[];
    matches: Record<string, PdfJsonResponse[]>;
  }>;
}

function DropdownRadio({
  selectId,
  tableViewData,
}: {
  selectId: string;
  tableViewData: TableViewData;
}) {
  // TODO: https://flowbite.com/docs/forms/radio/#radio-in-dropdown
  return (
    <div>
      { tableViewData.header.map(tableHeaderItem => {
        const inputId = `${selectId}-${tableHeaderItem}`;
        return (
          <div key={inputId}>
            <input type="radio" name={inputId} value={tableHeaderItem} checked={true} onChange={() => {}} />
            <label htmlFor={selectId}>{tableHeaderItem}</label>
          </div>
        );
      })}
    </div>
  );
}

type TableData = {
  doors?: TableViewData;
  doorCount: number;
  windows?: TableViewData;
  windowCount: number;
};

function TableView({
  tableViewData,
  id
}: {
  tableViewData: TableViewData;
  id: string;
}) {
  const selectId = `${id}-group-select`;
  return (
    <div>
      <div className="flex flex-row">
        <label htmlFor={selectId} className="mx-5">Group By</label>
        <button type="button" className="mx-5">
          Select All
        </button>
        <button type="button" className="mx-5">
          Deselect All
        </button>
        <DropdownRadio selectId={selectId} tableViewData={tableViewData} />
      </div>

      <table className="table-auto">
        <thead>
          <tr>
            <th key={`${id}-count`}></th>
            { tableViewData.header.map(headerItem => {
              return (
                <th key={`${id}-${headerItem}`}>{headerItem}</th>
              )
            })}
          </tr>

        </thead>
        <tbody>
          { tableViewData.rows
              .filter(row => {
                return row.row.length > 0;
              })
              .map(row => {
                const rowId = row.row[0];
                const instancesOfThisRow: PdfJsonResponse[] = Array.prototype.concat.apply([], Object.values(row.matches));
                return instancesOfThisRow.map((rowInstance, idx) => {
                      const instanceId = `${id}-${rowId}-${idx}`;
                      return (
                        <tr key={instanceId}>
                          <th key={`${instanceId}-count`}>{ idx === 0 ? instancesOfThisRow.length : ""}</th>
                          { row.row.map((rowValue, idx) => {
                            const columnHeader = tableViewData.header[idx];
                            return (
                              <th key={`${instanceId}-${columnHeader}`}>{rowValue}</th>
                            );
                          })}
                        </tr>
                      );
                    })
                })
          }
        </tbody>
      </table>
    </div>

  )
}

function makeTableDataRows({
  schedule,
  matchesAllPages,
}: {
  schedule: {
    header: string[];
    rows: string[][];
  };
  matchesAllPages: Record<string, Record<string, PdfJsonResponse[]>>;
}) {
  return {
    header: schedule.header,
    rows: schedule.rows
      .filter(row => {
        return row.length > 0 && row[0].trim().length > 0;
      })
      .map(row => {
        const rowId = row[0];
        let matches = {};
        if (rowId in matchesAllPages) {
          matches = matchesAllPages[rowId];
        }
        return {
          row,
          matches,
        }
      }),
  }
}



function makeTableData({
  pdfSummary,
}: {
  pdfSummary: CompletePdfSummary;
}) {
  const {
    doors,
    doorSchedule,
    windows,
    windowSchedule,
  } = pdfSummary.pdfSummary;
  const doorsAllPages = mergeRecordItems(doors);
  const windowsAllPages = mergeRecordItems(windows);
  const out: TableData = {
    doorCount: countsForObj(doorsAllPages),
    windowCount: countsForObj(windowsAllPages),
  };
  if (doorSchedule) {
    out["doors"] = makeTableDataRows({
      schedule: doorSchedule,
      matchesAllPages: doorsAllPages,
    });
  }
  if (windowSchedule) {
    out["windows"] = makeTableDataRows({
      schedule: windowSchedule,
      matchesAllPages: windowsAllPages,
    });
  }
  return out;
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
  const tableData = makeTableData({
    pdfSummary,
  });
  const doorsAllPagesCount = tableData.doorCount;
  const windowsAllPagesCount = tableData.windowCount;
  const items = [{
    id: "Doors",
    heading: (
      <>
        <div className="overflow-clip">Doors</div>
        <div className="overflow-clip">x {doorsAllPagesCount}</div>
      </>
    ),
    body: (
      <>
        { tableData.doors && (
          <TableView id="Doors" tableViewData={tableData.doors} />
        )}
      </>
    )
  }, {
    id: "Windows",
    heading: (
      <>
        <div className="overflow-clip">Windows</div>
        <div className="overflow-clip">x {windowsAllPagesCount}</div>
      </>
    ),
    body: (
      <>
        { tableData.windows && (
          <TableView id="Windows" tableViewData={tableData.windows} />
        )}
      </>
    )
  }];
  return (
    <div className="m-4">
      { items.map((item, idx) => {
        return (
          <Accordion item={item} key={item.id} id={item.id} isFirst={idx === 0} isLast={idx === items.length - 1}  />
        );
      })}
    </div>
  )
}