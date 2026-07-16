"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiFetch } from "@/lib/api/client";
import { Button } from "@/components/ui/Button";
import {
  applyTemplateMapping,
  headerSignature,
  type ImportTemplate,
} from "@/lib/importTemplates";
import type { Mapping } from "@/lib/normalizeImportRows";

interface Props {
  headers: string[];
  effectiveMapping: Mapping;
  onApply: (mapping: Mapping) => void;
}

/**
 * Saved-template bar for the import mapping step (P5-IMP-FUP-2): pick a
 * previously saved column-mapping template and apply it, save the current
 * mapping under a name, or delete a stale template. Templates whose
 * source signature matches the current headers sort first.
 */
export function ImportTemplateControls({ headers, effectiveMapping, onApply }: Props) {
  const queryClient = useQueryClient();
  const signature = headerSignature(headers);

  const [selectedId, setSelectedId] = useState("");
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const templates = useQuery<ImportTemplate[]>({
    queryKey: ["import-templates"],
    queryFn: () => apiFetch<ImportTemplate[]>("/api/imports/templates", { silent: true }),
  });

  const sorted = [...(templates.data ?? [])].sort((a, b) => {
    const aMatch = a.source_signature === signature ? 0 : 1;
    const bMatch = b.source_signature === signature ? 0 : 1;
    return aMatch - bMatch || a.name.localeCompare(b.name);
  });
  const selected = sorted.find((t) => t.id === selectedId) ?? null;

  // 409 (duplicate name) and 422 render inline, not as a toast.
  const create = useMutation<ImportTemplate, Error, void>({
    mutationFn: () =>
      apiFetch<ImportTemplate>("/api/imports/templates", {
        method: "POST",
        silent: true,
        body: {
          name: name.trim(),
          source_signature: signature,
          mapping: effectiveMapping,
        },
      }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["import-templates"] });
      setSelectedId(created.id);
      setSaving(false);
      setName("");
      setError(null);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not save template"),
  });

  const remove = useMutation<unknown, Error, string>({
    mutationFn: (id) =>
      apiFetch(`/api/imports/templates/${id}`, { method: "DELETE", silent: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["import-templates"] });
      setSelectedId("");
      setError(null);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not delete template"),
  });

  return (
    <div className="border border-slate-200 rounded-lg px-3 py-2 space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-[12px]">
        <span className="text-slate-600 font-medium">Mapping template:</span>
        <select
          value={selectedId}
          onChange={(e) => {
            setSelectedId(e.target.value);
            setError(null);
          }}
          disabled={templates.isLoading || sorted.length === 0}
          className="border border-slate-200 rounded px-2 py-1 text-[12px] max-w-[240px]"
        >
          <option value="">
            {templates.isLoading
              ? "Loading…"
              : sorted.length === 0
                ? "No saved templates"
                : "— choose a template —"}
          </option>
          {sorted.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
              {t.source_signature === signature ? " (matches these columns)" : ""}
            </option>
          ))}
        </select>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={selected === null}
          onClick={() => {
            if (selected) onApply(applyTemplateMapping(selected, headers));
          }}
        >
          Apply
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={selected === null || remove.isPending}
          onClick={() => {
            if (selected) remove.mutate(selected.id);
          }}
        >
          Delete
        </Button>

        <span className="mx-1 text-slate-300">|</span>

        {saving ? (
          <>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && name.trim() !== "" && !create.isPending) {
                  create.mutate();
                }
              }}
              placeholder="Template name"
              className="border border-slate-200 rounded px-2 py-1 text-[12px] w-44"
            />
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={name.trim() === "" || create.isPending}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "Saving…" : "Save"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                setSaving(false);
                setName("");
                setError(null);
              }}
            >
              Cancel
            </Button>
          </>
        ) : (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              setSaving(true);
              setError(null);
            }}
          >
            Save current mapping…
          </Button>
        )}
      </div>

      {templates.isError && (
        <div className="text-[12px] text-slate-500">
          Couldn’t load saved templates — you can still map columns manually.
        </div>
      )}
      {error && (
        <div className="text-[12px] text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">
          {error}
        </div>
      )}
    </div>
  );
}
