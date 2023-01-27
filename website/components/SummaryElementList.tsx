

import { useState } from "react";
import { CompletePdfSummary, PdfJsonResponse, PdfSummaryJson } from "../utils/requestresponsetypes";

function ChevronDown() {
  return (
    <svg data-accordion-icon className="w-6 h-6 shrink-0" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd"></path>
    </svg>
  )
}
function ChevronUp() {
  return (
    <svg data-accordion-icon className="w-6 h-6 rotate-180 shrink-0" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd"></path>
    </svg>
  );
}

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
          { isOpen ? <ChevronUp /> : <ChevronDown /> }
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
  radioStates,
  setRadioStates,
}: {
  selectId: string;
  tableViewData: TableViewData;
  radioStates: Record<number, boolean>;
  setRadioStates: React.Dispatch<React.SetStateAction<Record<number, boolean>>>;
}) {
  function toggleOption(optionIdx: number) {
    setRadioStates({
      ...radioStates,
      [optionIdx]: !radioStates[optionIdx],
    });
  }
  return (
    <div className="h-[62px] w-[200px]">
      <div className="absolute w-[200px]">
        <div className="group flex flex-col items-end">
          <button type="button" className="border rounded-xl px-4 py-2 flex flex-row text-gray-600">
            <span>Group By </span>
            <div className="">
              <ChevronDown />
            </div>
          </button>
          <div className="hidden group-hover:flex group-hover:flex-col z-10 bg-white border rounded-lg w-fit h-fit p-6 -ml-3">
            { tableViewData.header.map((tableHeaderItem, headerItemIdx) => {
              const inputId = `${selectId}-${tableHeaderItem}`;
              return (
                <div key={inputId} onClick={() => toggleOption(headerItemIdx)}>
                  <input type="radio"
                    name={inputId}
                    value={tableHeaderItem}
                    checked={radioStates[headerItemIdx]}
                    onChange={() => {}}/>
                  <label htmlFor={selectId}>{tableHeaderItem}</label>
                </div>
              );
            })}
          </div>
        </div>
      </div>
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
  id,
  tableViewData,
  setJumpToPosition,
}: {
  id: string;
  tableViewData: TableViewData;
  setJumpToPosition: (args: {
    page: number;
    bbox: [number, number, number, number];
  }) => void;
}) {
  const selectId = `${id}-group-select`;
  const options = tableViewData.header.reduce((obj, tableHeaderItem, idx) => {
    obj[idx] = idx > 0;
    return obj;
  }, {} as Record<number, boolean>);
  const [ radioStates, setRadioStates ] = useState(options);
  const groups: Record<string, {
    header: string[];
    match: PdfJsonResponse;
  }[]> = {};
  const selectedRadioStates = Object.entries(radioStates)
    .filter(([headerIdx, radioSelected]) => {
      return radioSelected;
    })
    .map(([headerIdx, radioSelected]) => {
      return Number(headerIdx);
    });
  selectedRadioStates.sort((headerIdxLeft, headerIdxRight) => {
    return headerIdxLeft - headerIdxRight;
  })
  tableViewData.rows
    .filter(row => {
      if (row.row.length === 0) {
        return false;
      }
      const rowId = row.row[0];
      return rowId.trim().length > 0;
    })
    .forEach(row => {
      const instancesOfThisRow: PdfJsonResponse[] = Array.prototype.concat.apply([], Object.values(row.matches));
      const groupId = selectedRadioStates.map((headerIdx) => {
        return row.row[headerIdx]
      }).join("-");
      if (!(groupId in groups)) {
        groups[groupId] = [];
      }
      instancesOfThisRow.forEach(rowInstance => {
        groups[groupId].push({
          header: row.row,
          match: rowInstance,
        });
      });
    });
  const groupsArray = Object.entries(groups);
  groupsArray.forEach(([groupId, groupValues]) => {
    groupValues.sort((left, right) => {
      const leftId = left.match.label || "zzz";
      const rightId = right.match.label || "zzz";
      if (leftId < rightId) {
        return -1;
      }
      if (leftId === rightId) {
        return 0;
      }
      return 1;
    });
  })
  groupsArray.sort(([groupIdLeft, groupValuesLeft], [groupIdRight, groupValuesRight]) => {
    // Put empty results at the end
    if (groupValuesLeft.length === 0 && groupValuesRight.length > 0) {
      return 1;
    }
    else if (groupValuesLeft.length === 0 && groupValuesRight.length === 0) {
      return 0;
    }
    else if (groupValuesLeft.length > 0 && groupValuesRight.length === 0) {
      return -1;
    }
    const leftId = groupValuesLeft[0].match.label || "zzz";
    const rightId = groupValuesRight[0].match.label || "zzz";
    if (leftId < rightId) {
      return -1;
    }
    else if (leftId === rightId) {
      return 0;
    }
    else {
      return 1;
    }
  });
  return (
    <div className="overflow-x-scroll">
      <div className="flex flex-col items-end">
        <DropdownRadio selectId={selectId}
          tableViewData={tableViewData}
          radioStates={radioStates}
          setRadioStates={setRadioStates} />
      </div>

      <table className="table-auto text-sm">
        <thead>
          <tr>
            <th key={`${id}-count`} className="pr-2">Counts</th>
            { tableViewData.header.map(headerItem => {
              return (
                <th key={`${id}-${headerItem}`}
                  className="px-2">{headerItem}</th>
              );
            })}
          </tr>
        </thead>
        <tbody className="">
          { groupsArray
            .map(([groupId, groupValues]) => {
              const instanceElems = [...groupValues.map((groupInstance, idxInGroup) => {
                const rowId = groupInstance.header[0];
                const instanceId = `${id}-${rowId}-${idxInGroup}`;
                return (
                  <tr key={instanceId}
                    className={`${idxInGroup === 0 ? "border-t" : ""}`}
                    onMouseEnter={() => {
                      setJumpToPosition({
                        page: groupInstance.match.page_number,
                        bbox: groupInstance.match.bbox,
                      });
                    }}>
                    <th key={`${instanceId}-count`}
                      className="font-normal">{idxInGroup === 0 ? groupValues.length : ""}</th>
                    { groupInstance.header.map((headerValue, columnIdx) => {
                      const headerName = tableViewData.header[columnIdx];
                      return (
                        <th key={`${instanceId}-${headerName}`}
                          className="font-normal">{columnIdx === 0 ? groupInstance.match.label : headerValue}</th>
                      );
                    })}
                  </tr>
                )
              }), (
                <tr key={`${groupId}-spacer`} className="h-5" />
              )];
              return instanceElems;
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
  setJumpToPosition,
}: {
  pdfSummary: CompletePdfSummary;
  setJumpToPosition: (args: {
      page: number;
      bbox: [number, number, number, number];
  }) => void;
}) {
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
          <TableView id="Doors" tableViewData={tableData.doors} setJumpToPosition={setJumpToPosition} />
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
          <TableView id="Windows" tableViewData={tableData.windows} setJumpToPosition={setJumpToPosition} />
        )}
      </>
    )
  }];
  return (
    <div className="w-full p-4">
      { items.map((item, idx) => {
        return (
          <Accordion item={item} key={item.id} id={item.id} isFirst={idx === 0} isLast={idx === items.length - 1}  />
        );
      })}
    </div>
  )
}