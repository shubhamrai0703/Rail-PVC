"use client";

import { useState, type ReactNode } from "react";
import { AlertTriangle, Check, FileWarning, Pencil, X } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import type {
  Confidence,
  Extracted,
  FieldState,
  SourceRef,
} from "@/lib/wireframes/extraction";
import { isBlocking } from "@/lib/wireframes/extraction";

/**
 * Where a proposed value came from. This is deliberately not collapsible and not
 * a tooltip — a value whose provenance is one hover away is a value people stop
 * checking. Every proposed number on every screen carries one of these.
 */
export function SourceChip({ source }: { source: SourceRef | null }) {
  if (!source) {
    return (
      <span className="text-[11px] text-slate-400 italic">no source — nothing was extracted</span>
    );
  }
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-1.5 text-[11px] text-slate-500">
      <span className="font-medium text-slate-600">{source.doc}</span>
      {source.page !== null && (
        <span className="font-mono text-slate-500">p.{source.page}</span>
      )}
      <span className="text-slate-400">·</span>
      <span className="italic">{source.locator}</span>
    </span>
  );
}

const CONFIDENCE_LABEL: Record<Confidence, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

const CONFIDENCE_STYLE: Record<Confidence, string> = {
  high: "bg-green-500",
  medium: "bg-amber-500",
  low: "bg-red-500",
};

export function ConfidenceDot({ confidence }: { confidence: Confidence }) {
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] text-slate-500"
      title={CONFIDENCE_LABEL[confidence]}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", CONFIDENCE_STYLE[confidence])} />
      {CONFIDENCE_LABEL[confidence]}
    </span>
  );
}

export function StateBadge({ state }: { state: FieldState }) {
  switch (state) {
    case "confirmed":
      return <Badge variant="approved">Confirmed</Badge>;
    case "rejected":
      return <Badge variant="neutral">Entered by hand</Badge>;
    case "conflict":
      return <Badge variant="blocked">Conflict</Badge>;
    case "missing":
      return <Badge variant="blocked">Missing</Badge>;
    case "unreadable":
      return <Badge variant="blocked">Unreadable</Badge>;
    default:
      return <Badge variant="draft">Proposed</Badge>;
  }
}

/**
 * The blocking banner. Missing / conflicting / unreadable values must never
 * silently become 0 or blank, so every one of them surfaces here with a reason
 * and a way out.
 */
export function BlockedCallout({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2.5">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-600" strokeWidth={2} />
        <div className="min-w-0 flex-1">
          <p className="text-[12px] font-medium text-red-900">{title}</p>
          {children && (
            <div className="mt-1 text-[12px] leading-5 text-red-800">{children}</div>
          )}
          {action && <div className="mt-2 flex flex-wrap gap-2">{action}</div>}
        </div>
      </div>
    </div>
  );
}

export function LowConfidenceCallout({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
      <div className="flex items-start gap-2">
        <FileWarning className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" strokeWidth={2} />
        <div className="min-w-0 flex-1 text-[12px] leading-5 text-amber-900">{children}</div>
      </div>
    </div>
  );
}

/**
 * The escape hatch. Reachable from every screen, by requirement — extraction is
 * an accelerator, never the only path to a value.
 */
export function ManualEntryEscape({
  label = "Skip extraction — enter this by hand",
  onUse,
}: {
  label?: string;
  onUse?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onUse}
      className="inline-flex items-center gap-1.5 text-[12px] text-slate-600 underline decoration-slate-300 underline-offset-2 hover:text-slate-900 focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600"
    >
      <Pencil className="h-3 w-3" strokeWidth={1.75} />
      {label}
    </button>
  );
}

/** Common parsers for the inline manual-entry input. */
export function parseText(raw: string): string | null {
  const trimmed = raw.trim();
  return trimmed === "" ? null : trimmed;
}

export function parseNumber(raw: string): number | null {
  const cleaned = raw.replace(/[^0-9.\-]/g, "");
  if (cleaned === "" || cleaned === "-" || cleaned === ".") return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

export type FieldRowProps<T> = {
  label: string;
  /** One line explaining what the field means, in the user's language. */
  help?: string;
  field: Extracted<T>;
  /** Renders the value. Kept separate so money, dates and booleans each format properly. */
  format: (value: T) => ReactNode;
  /** Marks this as financially meaningful — requires explicit confirmation. */
  highStakes?: boolean;
  onConfirm?: () => void;
  onReject?: () => void;
  onResolve?: (value: T) => void;
  /**
   * Accepts a value the user typed. Supplying this (with `parse` or `choices`)
   * is what turns "Reject" into "reject and type the right value here".
   */
  onEnterManually?: (value: T) => void;
  /** Turns raw input text into a value. Ignored when `choices` is supplied. */
  parse?: (raw: string) => T | null;
  /** Fixed set of values — rendered as buttons instead of a free-text input. */
  choices?: readonly { value: T; label: string }[];
  /** Placeholder / format hint for the manual input. */
  inputHint?: string;
};

/**
 * One proposed field: value, provenance, confidence, state, and the controls to
 * accept it, reject it, or resolve a disagreement between documents.
 */
export function FieldRow<T>({
  label,
  help,
  field,
  format,
  highStakes = false,
  onConfirm,
  onReject,
  onResolve,
  onEnterManually,
  parse,
  choices,
  inputHint,
}: FieldRowProps<T>) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const blocked = isBlocking(field.state);
  const settled = field.state === "confirmed" || field.state === "rejected";
  const canEditHere = Boolean(onEnterManually) && Boolean(parse || choices);

  /**
   * A field with no value and nothing to choose between is a dead end unless the
   * input is already open. That covers a rejected proposal, a value no document
   * contained, and a page that could not be read — in none of those cases is
   * there anything for the user to click first.
   */
  const hasAlternatives = (field.alternatives?.length ?? 0) > 0;
  const awaitingManualValue =
    field.value === null &&
    !hasAlternatives &&
    (field.state === "rejected" ||
      field.state === "missing" ||
      field.state === "unreadable");
  const showEditor = canEditHere && (editing || awaitingManualValue);

  function commit(value: T) {
    onEnterManually?.(value);
    setEditing(false);
    setDraft("");
  }

  function handleReject() {
    setEditing(true);
    onReject?.();
  }

  const parsedDraft = parse ? parse(draft) : null;

  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2.5",
        blocked
          ? "border-red-200 bg-red-50/40"
          : field.state === "confirmed"
            ? "border-green-200 bg-green-50/40"
            : "border-slate-200 bg-white",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[12px] font-medium text-slate-700">{label}</span>
            {highStakes && (
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-800">
                Affects the calculation
              </span>
            )}
            <StateBadge state={field.state} />
          </div>

          <div className="mt-1 font-mono text-[15px] tabular-nums text-slate-900">
            {field.value === null ? (
              <span className="font-sans text-[13px] italic text-slate-400">
                nothing extracted — blank, not zero
              </span>
            ) : (
              format(field.value)
            )}
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
            {field.state === "rejected" ? (
              <span className="text-[11px] text-slate-500">
                Entered by hand — no document backs this value
              </span>
            ) : (
              <SourceChip source={field.source} />
            )}
            {!settled && <ConfidenceDot confidence={field.confidence} />}
          </div>

          {help && <p className="mt-1.5 text-[11px] leading-4 text-slate-500">{help}</p>}
        </div>

        <div className="flex shrink-0 gap-1.5">
          {!settled && !blocked && (
            <>
              <Button size="sm" variant="secondary" onClick={onConfirm}>
                <Check className="h-3 w-3" strokeWidth={2} />
                Confirm
              </Button>
              <Button size="sm" variant="ghost" onClick={handleReject}>
                <X className="h-3 w-3" strokeWidth={2} />
                {canEditHere ? "Reject & type" : "Reject"}
              </Button>
            </>
          )}
          {field.state === "rejected" && field.value !== null && !editing && canEditHere && (
            <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
              <Pencil className="h-3 w-3" strokeWidth={2} />
              Edit
            </Button>
          )}
        </div>
      </div>

      {/* Inline manual entry — the value gets typed where it is read. */}
      {showEditor && (
        <div className="mt-2.5 rounded-lg border border-slate-300 bg-white px-3 py-2.5">
          <p className="text-[11px] font-medium text-slate-700">
            Enter {label.toLowerCase()} yourself
          </p>
          {choices ? (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {choices.map((choice, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => commit(choice.value)}
                  className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[12px] text-slate-700 transition-colors hover:bg-slate-100"
                >
                  {choice.label}
                </button>
              ))}
            </div>
          ) : (
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <input
                autoFocus
                value={draft}
                placeholder={inputHint}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && parsedDraft !== null) commit(parsedDraft);
                  if (e.key === "Escape") setEditing(false);
                }}
                className="w-56 rounded border border-slate-300 px-2 py-1 font-mono text-[13px] text-slate-900"
              />
              <Button
                size="sm"
                variant="secondary"
                disabled={parsedDraft === null}
                onClick={() => parsedDraft !== null && commit(parsedDraft)}
              >
                Save
              </Button>
              {!awaitingManualValue && (
                <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
                  Cancel
                </Button>
              )}
            </div>
          )}
          {inputHint && !choices && (
            <p className="mt-1 text-[11px] text-slate-500">{inputHint}</p>
          )}
        </div>
      )}

      {blocked && (
        <div className="mt-2.5 space-y-2">
          <BlockedCallout
            title={
              field.state === "conflict"
                ? "Two documents disagree"
                : field.state === "unreadable"
                  ? "This page could not be read"
                  : "Not found in any uploaded document"
            }
          >
            {field.note}
          </BlockedCallout>

          {field.alternatives && field.alternatives.length > 0 && (
            <ul className="space-y-1.5">
              {field.alternatives.map((alt, i) => (
                <li
                  key={i}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="font-mono text-[13px] tabular-nums text-slate-900">
                      {format(alt.value)}
                    </div>
                    <SourceChip source={alt.source} />
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => onResolve?.(alt.value)}
                  >
                    Use this one
                  </Button>
                </li>
              ))}
            </ul>
          )}

          {!showEditor && (
            <ManualEntryEscape
              label={
                canEditHere
                  ? "None of these are right — type the value myself"
                  : "Skip extraction — enter this by hand"
              }
              onUse={handleReject}
            />
          )}
        </div>
      )}
    </div>
  );
}

/** Section heading used across the extraction steps. */
export function SectionHeading({
  title,
  description,
  aside,
}: {
  title: string;
  description?: string;
  aside?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-[15px] font-semibold tracking-tight text-slate-900">{title}</h2>
        {description && (
          <p className="mt-0.5 max-w-2xl text-[12px] leading-5 text-slate-500">{description}</p>
        )}
      </div>
      {aside}
    </div>
  );
}

/**
 * Flags a field that the screens propose but the schema cannot store yet.
 * Used for per-item escalation %, which the tabulation statement prints but
 * `contract_items` has no column for.
 */
export function SchemaGapNote({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-violet-300 bg-violet-50 px-3 py-2 text-[11px] leading-4 text-violet-900">
      <span className="font-medium">Open schema decision — not stored today. </span>
      {children}
    </div>
  );
}
