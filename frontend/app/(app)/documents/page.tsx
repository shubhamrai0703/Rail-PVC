import { FolderClosed } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";

export default function DocumentsPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Document Vault
        </h1>
        <p className="text-[13px] text-slate-500 mt-1">
          Agreements, MBs, bills, and recovery memos. Store-only in v1 — no parsing.
        </p>
      </header>

      <EmptyState
        icon={<FolderClosed className="h-4 w-4" strokeWidth={1.75} />}
        title="No documents yet"
        description="Upload arrives in Phase 5 (P5-006) once Supabase Storage is wired through the API."
      />
    </div>
  );
}
