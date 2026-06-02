"use client";

import { useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import type { ParsedRow, SteelSubtype } from "@/lib/parseTsvImport";
import {
  TARGET_FIELDS,
  fuzzyHeaderMap,
  REQUIRED_FIELDS,
  type TargetField,
} from "@/lib/fuzzyHeaderMap";
import {
  normalizeImportRows,
  type Mapping,
} from "@/lib/normalizeImportRows";
import type { XlsxWorkbook } from "@/lib/parseXlsx";

type ImportedRow = ParsedRow & { _rowState: "new" };

interface Props {
  onClose: () => void;
  onAdd: (rows: ImportedRow[]) => void;
}

type SourceMode = "file" | "paste";

interface SourceData {
  headers: string[];
  body: string[][];
}

function parseTsvToMatrix(raw: string): string[][] {
  return raw
    .split(/\r?\n/)
    .filter((line) => line.length > 0)
    .map((line) => line.split("\t").map((c) => c.trim()));
}

const FIELD_LABEL: Record<TargetField, string> = {
  item_code: "Item code",
  description: "Description",
  unit: "Unit",
  original_qty: "Original qty",
  revised_qty: "Revised qty",
  base_rate: "Base rate",
  agreement_rate: "Agreement rate",
  is_cement_item: "Cement item",
  steel_subtype: "Steel subtype",
};

export function ImportRowsModal({ onClose, onAdd }: Props) {
  const [mode, setMode] = useState<SourceMode>("file");

  // --- File / xlsx path -----------------------------------------------------
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [workbook, setWorkbook] = useState<XlsxWorkbook | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [sheetIdx, setSheetIdx] = useState(0);
  const [headerRowIdx, setHeaderRowIdx] = useState(0);
  const [fileError, setFileError] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);

  // --- Paste path -----------------------------------------------------------
  const [pasteRaw, setPasteRaw] = useState("");
  const [pasteHasHeader, setPasteHasHeader] = useState(true);

  // --- Mapping state --------------------------------------------------------
  // Null target = ignore. Empty object = no source yet.
  const [mappingOverrides, setMappingOverrides] = useState<Mapping>({});

  async function handleFile(file: File) {
    setFileError(null);
    setParsing(true);
    try {
      const { parseXlsx } = await import("@/lib/parseXlsx");
      const wb = await parseXlsx(file);
      if (wb.sheets.length === 0) {
        setFileError("Workbook contained no sheets");
        setWorkbook(null);
        return;
      }
      setWorkbook(wb);
      setFileName(file.name);
      setSheetIdx(0);
      setHeaderRowIdx(0);
      setMappingOverrides({});
    } catch (e) {
      setFileError(
        `Could not read this file: ${e instanceof Error ? e.message : String(e)}`,
      );
      setWorkbook(null);
    } finally {
      setParsing(false);
    }
  }

  // Compute the active source (headers + body) given the current mode + state.
  const source: SourceData | null = useMemo(() => {
    if (mode === "file") {
      if (!workbook || workbook.sheets.length === 0) return null;
      const sheet = workbook.sheets[Math.min(sheetIdx, workbook.sheets.length - 1)];
      if (sheet.rows.length === 0) return { headers: [], body: [] };
      const headerRow = Math.min(headerRowIdx, sheet.rows.length - 1);
      const headers = sheet.rows[headerRow].map((h) => h.trim());
      const body = sheet.rows.slice(headerRow + 1);
      return { headers, body };
    }
    if (mode === "paste") {
      const matrix = parseTsvToMatrix(pasteRaw);
      if (matrix.length === 0) return null;
      if (pasteHasHeader) {
        return { headers: matrix[0], body: matrix.slice(1) };
      }
      // Synthesize generic headers so the mapper still has something to render.
      const width = matrix[0].length;
      const headers = Array.from({ length: width }, (_, i) => `Column ${i + 1}`);
      return { headers, body: matrix };
    }
    return null;
  }, [mode, workbook, sheetIdx, headerRowIdx, pasteRaw, pasteHasHeader]);

  // Reset overrides whenever the source headers change. React 19's
  // documented "adjust state during render" pattern — the guard ensures
  // we only re-run on a real change, avoiding the cascading-render
  // lint warning that useEffect+setState would trigger.
  const headersKey = source ? source.headers.join("\x1f") : "";
  const [lastHeadersKey, setLastHeadersKey] = useState<string | null>(null);
  if (headersKey !== lastHeadersKey) {
    setLastHeadersKey(headersKey);
    setMappingOverrides(
      source === null ? {} : fuzzyHeaderMap(source.headers).mapping,
    );
  }

  // Compute the effective mapping (overrides win).
  const effectiveMapping: Mapping = useMemo(() => {
    if (source === null) return {};
    const out: Mapping = {};
    for (const h of source.headers) {
      out[h] = h in mappingOverrides ? mappingOverrides[h] : null;
    }
    return out;
  }, [source, mappingOverrides]);

  const missingRequired = useMemo(() => {
    const mapped = new Set<TargetField>();
    for (const t of Object.values(effectiveMapping)) {
      if (t !== null) mapped.add(t);
    }
    return [...REQUIRED_FIELDS].filter((f) => !mapped.has(f));
  }, [effectiveMapping]);

  // Detect duplicate target assignments (UX warning).
  const duplicateTargets = useMemo(() => {
    const counts: Partial<Record<TargetField, number>> = {};
    for (const t of Object.values(effectiveMapping)) {
      if (t === null) continue;
      counts[t] = (counts[t] ?? 0) + 1;
    }
    return Object.entries(counts)
      .filter(([, n]) => (n ?? 0) > 1)
      .map(([t]) => t as TargetField);
  }, [effectiveMapping]);

  // Run the row normalizer for the preview / commit.
  const parsed = useMemo(() => {
    if (source === null || source.headers.length === 0) return null;
    if (missingRequired.length > 0 || duplicateTargets.length > 0) return null;
    return normalizeImportRows({
      mapping: effectiveMapping,
      rows: source.body,
    });
  }, [source, effectiveMapping, missingRequired, duplicateTargets]);

  const commit = () => {
    if (!parsed || parsed.rows.length === 0 || parsed.errors.length > 0) return;
    onAdd(parsed.rows.map((r) => ({ ...r, _rowState: "new" as const })));
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[92vh] overflow-auto p-6 space-y-4">
        <header className="flex items-center justify-between">
          <h2 className="text-[16px] font-semibold text-slate-900">
            Import rows from Excel
          </h2>
          <button
            type="button"
            className="text-slate-400 hover:text-slate-700 text-[18px]"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </header>

        {/* Step 1 — pick a source */}
        <div className="border-b border-slate-200">
          <nav className="-mb-px flex gap-4 text-[13px]">
            <TabButton
              active={mode === "file"}
              onClick={() => setMode("file")}
              label="Upload .xlsx"
            />
            <TabButton
              active={mode === "paste"}
              onClick={() => setMode("paste")}
              label="Paste from Excel"
            />
          </nav>
        </div>

        {mode === "file" && (
          <FilePicker
            fileInputRef={fileInputRef}
            fileName={fileName}
            parsing={parsing}
            fileError={fileError}
            workbook={workbook}
            sheetIdx={sheetIdx}
            headerRowIdx={headerRowIdx}
            setSheetIdx={setSheetIdx}
            setHeaderRowIdx={setHeaderRowIdx}
            onFile={handleFile}
          />
        )}

        {mode === "paste" && (
          <PasteArea
            raw={pasteRaw}
            setRaw={setPasteRaw}
            hasHeader={pasteHasHeader}
            setHasHeader={setPasteHasHeader}
          />
        )}

        {/* Step 2 — mapping */}
        {source !== null && source.headers.length > 0 && (
          <MappingTable
            source={source}
            mapping={effectiveMapping}
            onChange={(header, target) =>
              setMappingOverrides((prev) => ({ ...prev, [header]: target }))
            }
            onResetAuto={() => setMappingOverrides(fuzzyHeaderMap(source.headers).mapping)}
            missingRequired={missingRequired}
            duplicateTargets={duplicateTargets}
          />
        )}

        {/* Step 3 — preview + errors */}
        {parsed !== null && parsed.errors.length > 0 && (
          <div className="text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <div className="font-medium mb-1">Row parse errors:</div>
            <ul className="list-disc list-inside space-y-0.5">
              {parsed.errors.slice(0, 50).map((e, i) => (
                <li key={i}>{e}</li>
              ))}
              {parsed.errors.length > 50 && (
                <li>…and {parsed.errors.length - 50} more</li>
              )}
            </ul>
          </div>
        )}

        {parsed !== null && parsed.rows.length > 0 && (
          <Preview rows={parsed.rows} />
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            disabled={
              parsed === null ||
              parsed.rows.length === 0 ||
              parsed.errors.length > 0
            }
            onClick={commit}
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

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TabButton({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`pb-2 -mb-px border-b-2 ${
        active
          ? "border-slate-900 text-slate-900 font-medium"
          : "border-transparent text-slate-500 hover:text-slate-700"
      }`}
    >
      {label}
    </button>
  );
}

function FilePicker({
  fileInputRef,
  fileName,
  parsing,
  fileError,
  workbook,
  sheetIdx,
  headerRowIdx,
  setSheetIdx,
  setHeaderRowIdx,
  onFile,
}: {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  fileName: string;
  parsing: boolean;
  fileError: string | null;
  workbook: XlsxWorkbook | null;
  sheetIdx: number;
  headerRowIdx: number;
  setSheetIdx: (n: number) => void;
  setHeaderRowIdx: (n: number) => void;
  onFile: (file: File) => void;
}) {
  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files[0];
          if (f) onFile(f);
        }}
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center cursor-pointer hover:bg-slate-50"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFile(f);
          }}
        />
        <div className="text-[13px] text-slate-600">
          {fileName ? (
            <>
              <strong>{fileName}</strong>
              <div className="text-[12px] text-slate-500 mt-1">Click to replace</div>
            </>
          ) : (
            <>Drop an .xlsx file here, or click to browse</>
          )}
        </div>
      </div>
      {parsing && <div className="text-[12px] text-slate-500">Reading workbook…</div>}
      {fileError && (
        <div className="text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {fileError}
        </div>
      )}
      {workbook && workbook.sheets.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-[13px]">
          <label className="flex items-center gap-2">
            <span className="text-slate-600">Sheet:</span>
            <select
              value={sheetIdx}
              onChange={(e) => {
                setSheetIdx(Number(e.target.value));
                setHeaderRowIdx(0);
              }}
              className="border border-slate-200 rounded px-2 py-1"
            >
              {workbook.sheets.map((s, i) => (
                <option key={i} value={i}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2">
            <span className="text-slate-600">Header row:</span>
            <input
              type="number"
              min={1}
              max={Math.max(1, workbook.sheets[sheetIdx]?.rows.length ?? 1)}
              value={headerRowIdx + 1}
              onChange={(e) =>
                setHeaderRowIdx(Math.max(0, Number(e.target.value) - 1))
              }
              className="border border-slate-200 rounded px-2 py-1 w-20"
            />
          </label>
        </div>
      )}
    </div>
  );
}

function PasteArea({
  raw,
  setRaw,
  hasHeader,
  setHasHeader,
}: {
  raw: string;
  setRaw: (s: string) => void;
  hasHeader: boolean;
  setHasHeader: (b: boolean) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-[13px] text-slate-600">
        Copy a range from Excel (with header row), then paste it here.
      </p>
      <textarea
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        rows={8}
        className="w-full font-mono text-[12px] border border-slate-200 rounded-lg px-3 py-2"
        placeholder="Paste TSV here…"
      />
      <label className="inline-flex items-center gap-2 text-[12px] text-slate-600">
        <input
          type="checkbox"
          checked={hasHeader}
          onChange={(e) => setHasHeader(e.target.checked)}
        />
        First row contains column headers
      </label>
    </div>
  );
}

function MappingTable({
  source,
  mapping,
  onChange,
  onResetAuto,
  missingRequired,
  duplicateTargets,
}: {
  source: SourceData;
  mapping: Mapping;
  onChange: (header: string, target: TargetField | null) => void;
  onResetAuto: () => void;
  missingRequired: TargetField[];
  duplicateTargets: TargetField[];
}) {
  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="text-[13px] font-medium text-slate-700">
          Column mapping{" "}
          <span className="text-slate-500 font-normal">
            ({source.headers.length} source columns)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onResetAuto}
            className="text-[12px] text-slate-600 hover:text-slate-900 underline-offset-2 hover:underline"
          >
            Re-run auto-map
          </button>
          <span
            title="The AI-assisted mapper ships in the next release. Use the dropdowns to assign columns manually for now."
            className="cursor-help"
          >
            <Button type="button" variant="secondary" size="sm" disabled>
              🤖 Auto-map with AI
            </Button>
          </span>
        </div>
      </div>

      <table className="w-full text-[12px]">
        <thead className="text-slate-500 border-b border-slate-200">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Source header</th>
            <th className="px-3 py-2 text-left font-medium">Sample values</th>
            <th className="px-3 py-2 text-left font-medium">Maps to</th>
          </tr>
        </thead>
        <tbody>
          {source.headers.map((header, i) => {
            const samples = source.body
              .slice(0, 3)
              .map((r) => r[i] ?? "")
              .filter((v) => v !== "");
            return (
              <tr key={i} className="border-t border-slate-100">
                <td className="px-3 py-2 font-medium text-slate-800">
                  {header || <span className="text-slate-400">(empty header)</span>}
                </td>
                <td className="px-3 py-2 text-slate-500 truncate max-w-[260px]">
                  {samples.join(" · ") || <span className="text-slate-300">—</span>}
                </td>
                <td className="px-3 py-2">
                  <select
                    value={mapping[header] ?? ""}
                    onChange={(e) =>
                      onChange(
                        header,
                        e.target.value === "" ? null : (e.target.value as TargetField),
                      )
                    }
                    className="border border-slate-200 rounded px-2 py-1 text-[12px] w-full max-w-[220px]"
                  >
                    <option value="">— ignore —</option>
                    {TARGET_FIELDS.map((t) => (
                      <option key={t} value={t}>
                        {FIELD_LABEL[t]}
                        {REQUIRED_FIELDS.has(t) ? " *" : ""}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {(missingRequired.length > 0 || duplicateTargets.length > 0) && (
        <div className="px-3 py-2 text-[12px] bg-amber-50 border-t border-amber-200 text-amber-800 space-y-1">
          {missingRequired.length > 0 && (
            <div>
              Missing required:{" "}
              <span className="font-medium">
                {missingRequired.map((f) => FIELD_LABEL[f]).join(", ")}
              </span>
            </div>
          )}
          {duplicateTargets.length > 0 && (
            <div>
              Multiple columns map to:{" "}
              <span className="font-medium">
                {duplicateTargets.map((f) => FIELD_LABEL[f]).join(", ")}
              </span>{" "}
              — pick one.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Preview({ rows }: { rows: ParsedRow[] }) {
  const shown = rows.slice(0, 10);
  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <div className="px-3 py-2 text-[12px] font-medium text-slate-700 bg-slate-50 border-b border-slate-200">
        Preview — first {shown.length} of {rows.length} row{rows.length === 1 ? "" : "s"}
      </div>
      <div className="max-h-56 overflow-auto">
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
            {shown.map((r, i) => (
              <tr key={i} className="border-t border-slate-100">
                <td className="px-2 py-1 font-mono">{r.item_code}</td>
                <td className="px-2 py-1 truncate max-w-[280px]">
                  {r.description}
                </td>
                <td className="px-2 py-1">{r.unit}</td>
                <td className="px-2 py-1 text-right">{r.original_qty ?? ""}</td>
                <td className="px-2 py-1 text-right">{r.revised_qty ?? ""}</td>
                <td className="px-2 py-1 text-right">{r.base_rate ?? ""}</td>
                <td className="px-2 py-1 text-right">
                  {r.agreement_rate ?? ""}
                </td>
                <td className="px-2 py-1">{r.is_cement_item ? "yes" : ""}</td>
                <td className="px-2 py-1">
                  {(r.steel_subtype as SteelSubtype) ?? ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
