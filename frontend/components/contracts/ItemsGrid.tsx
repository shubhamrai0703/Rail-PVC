"use client";

import { useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AgGridReact } from "ag-grid-react";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeQuartz,
  type ColDef,
  type IHeaderParams,
  type SelectionChangedEvent,
} from "ag-grid-community";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError } from "@/lib/api/client";
import {
  parseTsvImport,
  VALID_STEEL_SUBTYPES,
  type ParseResult,
  type SteelSubtype,
} from "@/lib/parseTsvImport";

ModuleRegistry.registerModules([AllCommunityModule]);

const gridTheme = themeQuartz.withParams({
  fontSize: 13,
  headerHeight: 36,
  rowHeight: 34,
});

interface ContractItem {
  id?: string;
  item_code: string;
  description: string;
  unit: string;
  original_qty: number | string | null;
  revised_qty: number | string | null;
  base_rate: number | string | null;
  agreement_rate: number | string | null;
  is_cement_item: boolean;
  steel_subtype: SteelSubtype;
}

// Per-row tracking. `_rowState` is local-only and is stripped before any
// request body is constructed. "new" rows POST, "dirty" rows PUT, "persisted"
// rows skip.
type RowStateTag = "new" | "dirty" | "persisted";
type RowState = ContractItem & {
  _rowState: RowStateTag;
};

function emptyRow(): RowState {
  return {
    item_code: "",
    description: "",
    unit: "",
    original_qty: null,
    revised_qty: null,
    base_rate: null,
    agreement_rate: null,
    is_cement_item: false,
    steel_subtype: null,
    _rowState: "new",
  };
}

function itemPayload(r: RowState) {
  return {
    item_code: r.item_code,
    description: r.description,
    unit: r.unit,
    original_qty: r.original_qty,
    revised_qty: r.revised_qty,
    base_rate: r.base_rate,
    agreement_rate: r.agreement_rate,
    is_cement_item: r.is_cement_item,
    steel_subtype: r.steel_subtype,
  };
}

// P5-F1 — column-header tooltip via a custom AG Grid headerComponent. No
// external tooltip lib; we lean on the browser's native `title` attribute.
function TooltipHeader(
  props: IHeaderParams & { tooltipText?: string },
) {
  return (
    <span className="inline-flex items-center gap-1">
      <span>{props.displayName}</span>
      {props.tooltipText && (
        <span
          title={props.tooltipText}
          className="text-slate-400 hover:text-slate-600 cursor-help"
          aria-label={props.tooltipText}
        >
          ⓘ
        </span>
      )}
    </span>
  );
}

function ImportRowsModal({
  onClose,
  onAdd,
}: {
  onClose: () => void;
  onAdd: (rows: RowState[]) => void;
}) {
  // The parent gates rendering on `importOpen`, so this component mounts
  // fresh each time the modal opens — no effect-driven state reset needed.
  const [raw, setRaw] = useState("");
  const [parsed, setParsed] = useState<ParseResult | null>(null);

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-auto p-6 space-y-4">
        <h2 className="text-[16px] font-semibold text-slate-900">
          Import rows from Excel
        </h2>
        <p className="text-[13px] text-slate-600">
          Copy a range from Excel, then paste it here. Columns must be in this
          order:
        </p>
        <pre className="text-[12px] bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 overflow-x-auto">
{`item_code | description | unit | original_qty | revised_qty | base_rate | agreement_rate | is_cement_item (TRUE/FALSE/YES/NO/1/0, blank=false) | steel_subtype (blank, ${VALID_STEEL_SUBTYPES.join(", ")})`}
        </pre>
        <textarea
          value={raw}
          onChange={(e) => {
            setRaw(e.target.value);
            setParsed(null);
          }}
          rows={10}
          className="w-full font-mono text-[12px] border border-slate-200 rounded-lg px-3 py-2"
          placeholder="Paste TSV here…"
        />
        {parsed && parsed.errors.length > 0 && (
          <div className="text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <div className="font-medium mb-1">Parse errors:</div>
            <ul className="list-disc list-inside space-y-0.5">
              {parsed.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </div>
        )}
        {parsed && parsed.rows.length > 0 && (
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-3 py-2 text-[12px] font-medium text-slate-700 bg-slate-50 border-b border-slate-200">
              Preview ({parsed.rows.length} row
              {parsed.rows.length === 1 ? "" : "s"})
            </div>
            <div className="max-h-48 overflow-auto">
              <table className="w-full text-[12px]">
                <thead className="text-slate-500">
                  <tr>
                    <th className="px-2 py-1 text-left">Code</th>
                    <th className="px-2 py-1 text-left">Description</th>
                    <th className="px-2 py-1 text-left">Unit</th>
                    <th className="px-2 py-1 text-right">Orig</th>
                    <th className="px-2 py-1 text-right">Rev</th>
                    <th className="px-2 py-1 text-right">Base</th>
                    <th className="px-2 py-1 text-right">Agt</th>
                    <th className="px-2 py-1 text-left">Cement</th>
                    <th className="px-2 py-1 text-left">Steel</th>
                  </tr>
                </thead>
                <tbody>
                  {parsed.rows.map((r, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-2 py-1 font-mono">{r.item_code}</td>
                      <td className="px-2 py-1">{r.description}</td>
                      <td className="px-2 py-1">{r.unit}</td>
                      <td className="px-2 py-1 text-right">
                        {r.original_qty ?? ""}
                      </td>
                      <td className="px-2 py-1 text-right">
                        {r.revised_qty ?? ""}
                      </td>
                      <td className="px-2 py-1 text-right">
                        {r.base_rate ?? ""}
                      </td>
                      <td className="px-2 py-1 text-right">
                        {r.agreement_rate ?? ""}
                      </td>
                      <td className="px-2 py-1">
                        {r.is_cement_item ? "yes" : ""}
                      </td>
                      <td className="px-2 py-1">{r.steel_subtype ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setParsed(parseTsvImport(raw))}
            disabled={raw.trim().length === 0}
          >
            Preview
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            // M-2: any parse error blocks the import. Adding only the "good"
            // rows would silently drop the others, which for financial line
            // items reads as "errors are non-fatal."
            disabled={
              !parsed ||
              parsed.rows.length === 0 ||
              parsed.errors.length > 0
            }
            onClick={() => {
              if (!parsed || parsed.rows.length === 0) return;
              if (parsed.errors.length > 0) return;
              onAdd(
                parsed.rows.map((r) => ({ ...r, _rowState: "new" as const })),
              );
              onClose();
            }}
          >
            {parsed && parsed.rows.length > 0
              ? `Add ${parsed.rows.length} row${parsed.rows.length === 1 ? "" : "s"}`
              : "Add rows"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function ItemsGrid({ scheduleId }: { scheduleId: string }) {
  const queryClient = useQueryClient();
  const itemsQuery = useQuery<ContractItem[]>({
    queryKey: ["schedule-items", scheduleId],
    queryFn: () =>
      apiFetch<ContractItem[]>(`/api/schedules/${scheduleId}/items`),
  });

  const [rows, setRows] = useState<RowState[]>([]);
  const [saveProgress, setSaveProgress] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [selectedCount, setSelectedCount] = useState(0);
  const [importOpen, setImportOpen] = useState(false);
  const [hydratedAt, setHydratedAt] = useState<number | null>(null);
  const gridRef = useRef<AgGridReact<RowState>>(null);

  // React 19 pattern for syncing external query state into local editable
  // state without a setState-in-effect: adjust state during render guarded by
  // a "did we already process this snapshot" check. Re-runs the render with
  // fresh rows when itemsQuery refetches; idempotent on subsequent renders.
  if (
    itemsQuery.data &&
    itemsQuery.dataUpdatedAt !== hydratedAt
  ) {
    setHydratedAt(itemsQuery.dataUpdatedAt);
    setRows(
      itemsQuery.data.map((r) => ({ ...r, _rowState: "persisted" as const })),
    );
    setSaveProgress(null);
    setSaveError(null);
    setSelectedCount(0);
  }

  const cementSteelConflicts = useMemo(
    () => rows.filter((r) => r.is_cement_item && r.steel_subtype),
    [rows],
  );

  const columnDefs = useMemo<ColDef<RowState>[]>(
    () => [
      {
        field: "item_code",
        headerName: "Code",
        editable: true,
        width: 130,
        checkboxSelection: true,
        headerCheckboxSelection: true,
      },
      {
        field: "description",
        headerName: "Description",
        editable: true,
        flex: 2,
      },
      { field: "unit", headerName: "Unit", editable: true, width: 80 },
      {
        field: "original_qty",
        headerName: "Orig qty",
        editable: true,
        width: 110,
        cellDataType: "number",
        headerComponent: TooltipHeader,
        headerComponentParams: {
          tooltipText:
            "Quantity as specified in the original LOA/agreement",
        },
      },
      {
        field: "revised_qty",
        headerName: "Rev qty",
        editable: true,
        width: 110,
        cellDataType: "number",
        headerComponent: TooltipHeader,
        headerComponentParams: {
          tooltipText:
            "Quantity after amendment or deviation order; used for billing when set",
        },
      },
      {
        field: "base_rate",
        headerName: "Base rate",
        editable: true,
        width: 120,
        cellDataType: "number",
        headerComponent: TooltipHeader,
        headerComponentParams: {
          tooltipText:
            "Schedule rate before bid discount (DSR/NS published rate)",
        },
      },
      {
        field: "agreement_rate",
        headerName: "Agreement rate",
        editable: true,
        width: 140,
        cellDataType: "number",
        headerComponent: TooltipHeader,
        headerComponentParams: {
          tooltipText:
            "Rate after applying the bid discount; this is the rate used in bills",
        },
      },
      {
        field: "is_cement_item",
        headerName: "Cement?",
        editable: true,
        width: 100,
        cellDataType: "boolean",
        headerComponent: TooltipHeader,
        headerComponentParams: {
          tooltipText:
            "Mark if this item falls under the cement PVC bucket (affects which price index series is applied)",
        },
      },
      {
        field: "steel_subtype",
        headerName: "Steel subtype",
        editable: true,
        width: 160,
        cellEditor: "agSelectCellEditor",
        cellEditorParams: {
          values: ["—", "angles", "plates", "other_sections", "tmt"],
        },
        valueParser: (p) => (p.newValue === "—" ? null : p.newValue),
        valueFormatter: (p) => p.value ?? "—",
        headerComponent: TooltipHeader,
        headerComponentParams: {
          tooltipText:
            "Mark if this item falls under the steel PVC bucket; the subtype maps to a specific steel index series",
        },
      },
    ],
    [],
  );

  function addRow() {
    setRows((prev) => [...prev, emptyRow()]);
  }

  function appendImportedRows(imported: RowState[]) {
    setRows((prev) => [...prev, ...imported]);
  }

  async function saveAll() {
    setSaveError(null);
    const work = rows
      .map((r, i) => ({ r, i }))
      .filter(({ r }) => r._rowState === "new" || r._rowState === "dirty");
    if (work.length === 0) {
      setSaveProgress("Nothing to save.");
      return;
    }
    let n = 0;
    // We update `rows` field-by-field at the end via a working copy so we
    // don't re-render during the iteration and lose AG Grid edit state.
    const next = [...rows];
    for (const { r, i } of work) {
      n += 1;
      setSaveProgress(`Saving ${n} of ${work.length}…`);
      try {
        if (r._rowState === "new") {
          const created = await apiFetch<{ id: string }>(
            `/api/schedules/${scheduleId}/items`,
            { method: "POST", body: itemPayload(r) },
          );
          next[i] = { ...next[i], id: created.id, _rowState: "persisted" };
        } else {
          // dirty + must have an id (loaded from server)
          await apiFetch(
            `/api/schedules/${scheduleId}/items/${r.id}`,
            { method: "PUT", body: itemPayload(r) },
          );
          next[i] = { ...next[i], _rowState: "persisted" };
        }
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? `Row ${i + 1} (${r.item_code || "<no code>"}): ${err.message}`
            : `Row ${i + 1}: save failed`;
        setSaveError(msg);
        setSaveProgress(null);
        setRows(next);
        return;
      }
    }
    setRows(next);
    setSaveProgress(`Saved ${work.length} row(s).`);
    queryClient.invalidateQueries({ queryKey: ["schedule-items", scheduleId] });
  }

  async function deleteSelected() {
    const api = gridRef.current?.api;
    if (!api) return;
    const selectedNodes = api.getSelectedNodes();
    if (selectedNodes.length === 0) return;

    const persistedSelected = selectedNodes.filter(
      (n) =>
        n.data?._rowState === "persisted" || n.data?._rowState === "dirty",
    );
    const newOnlySelected = selectedNodes.filter(
      (n) => n.data?._rowState === "new",
    );

    if (persistedSelected.length > 0) {
      const ok = window.confirm(
        `Delete ${persistedSelected.length + newOnlySelected.length} item(s)? This cannot be undone.`,
      );
      if (!ok) return;
    }

    setSaveError(null);
    // Track which rows survive.
    const toRemove = new Set<RowState>();
    for (const n of newOnlySelected) {
      if (n.data) toRemove.add(n.data);
    }
    for (const n of persistedSelected) {
      if (!n.data?.id) continue;
      try {
        await apiFetch(
          `/api/schedules/${scheduleId}/items/${n.data.id}`,
          { method: "DELETE" },
        );
        toRemove.add(n.data);
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? `Delete ${n.data.item_code || "<no code>"}: ${err.message}`
            : `Delete failed for ${n.data.item_code || "<no code>"}`;
        setSaveError(msg);
        break;
      }
    }
    setRows((prev) => prev.filter((r) => !toRemove.has(r)));
    api.deselectAll();
    setSelectedCount(0);
    if (persistedSelected.length > 0) {
      queryClient.invalidateQueries({
        queryKey: ["schedule-items", scheduleId],
      });
    }
  }

  return (
    <div className="space-y-3">
      {cementSteelConflicts.length > 0 && (
        <div className="text-[12px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          One or more items are marked as both a cement item and a steel item.
          Each item can only belong to one — please correct before saving.
        </div>
      )}

      <div className="flex items-center gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={addRow}>
          + Add row
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setImportOpen(true)}
        >
          Import rows
        </Button>
        {selectedCount > 0 && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={deleteSelected}
          >
            Delete selected ({selectedCount})
          </Button>
        )}
      </div>

      <div style={{ height: 480, width: "100%" }}>
        <AgGridReact<RowState>
          ref={gridRef}
          theme={gridTheme}
          rowData={rows}
          columnDefs={columnDefs}
          defaultColDef={{ resizable: true, sortable: true }}
          rowSelection="multiple"
          suppressRowClickSelection
          singleClickEdit
          stopEditingWhenCellsLoseFocus
          onSelectionChanged={(e: SelectionChangedEvent<RowState>) => {
            setSelectedCount(e.api.getSelectedNodes().length);
          }}
          onCellValueChanged={(e) => {
            const idx = e.rowIndex;
            if (idx === null) return;
            setRows((prev) => {
              const next = [...prev];
              const cur = next[idx];
              // A "new" row stays "new" — it has no server id yet. Only
              // "persisted" rows are demoted to "dirty" on edit.
              const tag: RowStateTag =
                cur._rowState === "new" ? "new" : "dirty";
              next[idx] = { ...cur, _rowState: tag };
              return next;
            });
          }}
        />
      </div>

      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="primary"
          size="sm"
          onClick={saveAll}
          // REVIEW.md M-3 — backend rejects cement+steel with 422 now, but
          // the client gate prevents a doomed round-trip and surfaces the
          // conflict before the user clicks Save.
          disabled={cementSteelConflicts.length > 0}
        >
          Save all
        </Button>
        {saveProgress && (
          <span className="text-[12px] text-slate-500">{saveProgress}</span>
        )}
        {saveError && (
          <span className="text-[12px] text-red-600">{saveError}</span>
        )}
      </div>

      {importOpen && (
        <ImportRowsModal
          onClose={() => setImportOpen(false)}
          onAdd={appendImportedRows}
        />
      )}
    </div>
  );
}
