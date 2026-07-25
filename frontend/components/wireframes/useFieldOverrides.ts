"use client";

import { useCallback, useState } from "react";
import type { Extracted, FieldState } from "@/lib/wireframes/extraction";

/**
 * Tracks what the user has done to each proposed field, keyed by a stable field
 * id. Wireframe-local only — this is what a real implementation would persist as
 * a pending-extraction record, never as a write to `contracts` / `bills`.
 */
export function useFieldOverrides() {
  const [states, setStates] = useState<Record<string, FieldState>>({});
  const [values, setValues] = useState<Record<string, unknown>>({});

  /** Merge any user decision over the extractor's proposal. */
  const effective = useCallback(
    <T,>(key: string, base: Extracted<T>): Extracted<T> => ({
      ...base,
      state: states[key] ?? base.state,
      value: key in values ? (values[key] as T) : base.value,
    }),
    [states, values],
  );

  const confirm = useCallback((key: string) => {
    setStates((prev) => ({ ...prev, [key]: "confirmed" }));
  }, []);

  const reject = useCallback((key: string) => {
    setStates((prev) => ({ ...prev, [key]: "rejected" }));
  }, []);

  /** Pick one side of a conflict. The chosen value is a confirmed extraction. */
  const resolve = useCallback((key: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setStates((prev) => ({ ...prev, [key]: "confirmed" }));
  }, []);

  /**
   * Take a value the user typed themselves. Stays `rejected` rather than
   * becoming `confirmed`: the number is now the user's, not the extractor's, and
   * the audit trail should not claim a document supports it.
   */
  const enterManually = useCallback((key: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setStates((prev) => ({ ...prev, [key]: "rejected" }));
  }, []);

  const confirmMany = useCallback((keys: string[]) => {
    setStates((prev) => {
      const next = { ...prev };
      for (const key of keys) next[key] = "confirmed";
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    setStates({});
    setValues({});
  }, []);

  return {
    effective,
    confirm,
    reject,
    resolve,
    enterManually,
    confirmMany,
    reset,
    states,
  };
}
