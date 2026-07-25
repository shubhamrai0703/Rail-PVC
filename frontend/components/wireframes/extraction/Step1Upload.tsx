"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, CircleDashed, FileText, ScanLine, Sheet } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import {
  DOC_KIND_LABEL,
  REQUIRED_DOC_KINDS,
  UPLOADED_DOCS,
  type DocKind,
  type TextLayer,
} from "@/lib/wireframes/extraction";
import {
  ConfidenceDot,
  LowConfidenceCallout,
  ManualEntryEscape,
  SectionHeading,
} from "@/components/wireframes/Primitives";

const TEXT_LAYER_COPY: Record<TextLayer, { label: string; blurb: string }> = {
  native: {
    label: "Spreadsheet",
    blurb: "Read directly from cells — the most reliable source we have.",
  },
  text: {
    label: "Digital text",
    blurb: "Has a text layer. Table structure still has to be interpreted.",
  },
  scanned: {
    label: "Scanned image",
    blurb: "No text layer. Nothing can be read from this without OCR.",
  },
};

function LayerIcon({ layer }: { layer: TextLayer }) {
  if (layer === "native") return <Sheet className="h-3.5 w-3.5" strokeWidth={1.75} />;
  if (layer === "scanned") return <ScanLine className="h-3.5 w-3.5" strokeWidth={1.75} />;
  return <FileText className="h-3.5 w-3.5" strokeWidth={1.75} />;
}

export function Step1Upload() {
  const [kinds, setKinds] = useState<Record<string, DocKind>>(() =>
    Object.fromEntries(UPLOADED_DOCS.map((d) => [d.id, d.proposedKind])),
  );
  const [excluded, setExcluded] = useState<Set<string>>(new Set());

  const assigned = useMemo(() => {
    const set = new Set<DocKind>();
    for (const doc of UPLOADED_DOCS) {
      if (excluded.has(doc.id)) continue;
      set.add(kinds[doc.id]);
    }
    return set;
  }, [kinds, excluded]);

  const missing = REQUIRED_DOC_KINDS.filter((k) => !assigned.has(k));
  const unclassified = UPLOADED_DOCS.filter(
    (d) => !excluded.has(d.id) && kinds[d.id] === "unknown",
  );
  const scanned = UPLOADED_DOCS.filter(
    (d) => !excluded.has(d.id) && d.textLayer === "scanned",
  );

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Upload and classify"
        description="Drop the whole bundle at once. We propose a type for each document — correct anything we got wrong before going further. Nothing is read from these documents until you move to the next step."
      />

      <div className="rounded-xl border border-dashed border-slate-300 bg-white px-5 py-6 text-center">
        <p className="text-[13px] font-medium text-slate-700">
          Drop agreement, LOA, tabulation statement, BOQ, MBs, bills and recoveries here
        </p>
        <p className="mt-1 text-[12px] text-slate-500">
          PDF, XLSX and images. 50 MB per file.
        </p>
      </div>

      {/* What the contract still needs. Answers "am I done uploading?" */}
      <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
          Documents this contract still needs
        </p>
        <ul className="mt-2 flex flex-wrap gap-2">
          {REQUIRED_DOC_KINDS.map((kind) => {
            const have = assigned.has(kind);
            return (
              <li
                key={kind}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px]",
                  have
                    ? "border-green-200 bg-green-50 text-green-800"
                    : "border-amber-200 bg-amber-50 text-amber-900",
                )}
              >
                {have ? (
                  <CheckCircle2 className="h-3 w-3" strokeWidth={2} />
                ) : (
                  <CircleDashed className="h-3 w-3" strokeWidth={2} />
                )}
                {DOC_KIND_LABEL[kind]}
              </li>
            );
          })}
        </ul>
        {missing.length > 0 && (
          <p className="mt-2 text-[12px] text-slate-600">
            {missing.length} document {missing.length === 1 ? "type is" : "types are"} still
            missing. You can continue without {missing.length === 1 ? "it" : "them"} — the
            fields they would have filled will be blank and blocked, not guessed.
          </p>
        )}
      </div>

      <ul className="space-y-2">
        {UPLOADED_DOCS.map((doc) => {
          const isExcluded = excluded.has(doc.id);
          const layer = TEXT_LAYER_COPY[doc.textLayer];
          return (
            <li
              key={doc.id}
              className={cn(
                "rounded-xl border px-4 py-3",
                isExcluded ? "border-slate-200 bg-slate-50 opacity-60" : "border-slate-200 bg-white",
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate text-[13px] font-medium text-slate-900">
                      {doc.filename}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10.5px] text-slate-600">
                      <LayerIcon layer={doc.textLayer} />
                      {layer.label}
                    </span>
                    {doc.proposedKind === "unknown" && !isExcluded && (
                      <Badge variant="blocked">Needs a type</Badge>
                    )}
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {doc.sizeLabel}
                    {doc.pages !== null && ` · ${doc.pages} pages`} · {layer.blurb}
                  </p>
                  <div className="mt-1">
                    <ConfidenceDot confidence={doc.confidence} />
                  </div>
                </div>

                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <label className="flex items-center gap-2 text-[11px] text-slate-500">
                    <span>Type</span>
                    <select
                      value={kinds[doc.id]}
                      disabled={isExcluded}
                      onChange={(e) =>
                        setKinds((prev) => ({
                          ...prev,
                          [doc.id]: e.target.value as DocKind,
                        }))
                      }
                      className="rounded border border-slate-200 px-2 py-1 text-[12px] text-slate-800 disabled:bg-slate-100"
                    >
                      {(Object.keys(DOC_KIND_LABEL) as DocKind[]).map((k) => (
                        <option key={k} value={k}>
                          {DOC_KIND_LABEL[k]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      setExcluded((prev) => {
                        const next = new Set(prev);
                        if (next.has(doc.id)) next.delete(doc.id);
                        else next.add(doc.id);
                        return next;
                      })
                    }
                    className="text-[11px] text-slate-500 underline decoration-slate-300 underline-offset-2 hover:text-slate-800"
                  >
                    {isExcluded ? "Include in extraction" : "Leave out of extraction"}
                  </button>
                </div>
              </div>

              {doc.note && !isExcluded && (
                <div className="mt-2">
                  <LowConfidenceCallout>{doc.note}</LowConfidenceCallout>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {(unclassified.length > 0 || scanned.length > 0) && (
        <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-[12px] font-medium text-slate-700">Before you continue</p>
          {unclassified.length > 0 && (
            <p className="text-[12px] leading-5 text-slate-600">
              {unclassified.length} document{unclassified.length === 1 ? "" : "s"} could not be
              classified. Give {unclassified.length === 1 ? "it" : "them"} a type or leave{" "}
              {unclassified.length === 1 ? "it" : "them"} out — an unclassified document is never
              read.
            </p>
          )}
          {scanned.length > 0 && (
            <p className="text-[12px] leading-5 text-slate-600">
              {scanned.length} document{scanned.length === 1 ? " is" : "s are"} scanned images.
              Expect their fields to arrive blank and blocked rather than guessed.
            </p>
          )}
        </div>
      )}

      <ManualEntryEscape label="Skip extraction — set this contract up by hand" />
    </div>
  );
}
