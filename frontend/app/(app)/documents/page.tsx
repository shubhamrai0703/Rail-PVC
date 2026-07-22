import { Suspense } from "react";
import { DocumentVault } from "@/components/documents/DocumentVault";

export default function DocumentsPage() {
  return (
    <Suspense fallback={<div className="py-12 text-center text-[13px] text-slate-400">Loading documents…</div>}>
      <DocumentVault />
    </Suspense>
  );
}
