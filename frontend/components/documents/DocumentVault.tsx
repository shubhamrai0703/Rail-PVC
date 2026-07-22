"use client";

import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, FolderClosed, Upload } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { apiFetch, apiUpload } from "@/lib/api/client";
import {
  DOCUMENT_TYPES,
  documentFileError,
  documentTypeLabel,
  type DocumentType,
  type VaultDocument,
} from "@/lib/documents";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";

interface ContractSummary {
  id: string;
  tender_number: string;
  contractor_name: string;
}

export function DocumentVault() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const contractId = searchParams.get("contract") ?? "";
  const [fileType, setFileType] = useState<DocumentType>("agreement");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const contractsQuery = useQuery<ContractSummary[]>({
    queryKey: ["contracts"],
    queryFn: () => apiFetch<ContractSummary[]>("/api/contracts"),
  });
  const documentsQuery = useQuery<VaultDocument[]>({
    queryKey: ["contract-documents", contractId],
    queryFn: () => apiFetch<VaultDocument[]>(`/api/contracts/${contractId}/documents`),
    enabled: contractId.length > 0,
  });

  const upload = useMutation({
    mutationFn: async (input: {
      contractId: string;
      file: File;
      fileType: DocumentType;
    }) => {
      const formData = new FormData();
      formData.append("file_type", input.fileType);
      formData.append("file", input.file);
      return apiUpload<VaultDocument>(`/api/contracts/${input.contractId}/documents`, formData);
    },
    onSuccess: async (_document, input) => {
      setFile(null);
      setFileError(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await queryClient.invalidateQueries({
        queryKey: ["contract-documents", input.contractId],
      });
    },
  });

  function selectContract(nextContractId: string) {
    setFile(null);
    setFileError(null);
    router.replace(
      nextContractId ? `/documents?contract=${encodeURIComponent(nextContractId)}` : "/documents",
      { scroll: false },
    );
  }

  function chooseFile(nextFile: File | null) {
    setFile(nextFile);
    setFileError(nextFile ? documentFileError(nextFile) : null);
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setFileError("Choose a file to upload.");
      return;
    }
    const validationError = documentFileError(file);
    if (validationError) {
      setFileError(validationError);
      return;
    }
    try {
      await upload.mutateAsync({ contractId, file, fileType });
    } catch {
      // apiUpload already surfaced a toast; the mutation error renders below.
    }
  }

  async function download(document: VaultDocument) {
    setDownloadingId(document.id);
    try {
      const { download_url: downloadUrl } = await apiFetch<{ download_url: string }>(
        `/api/documents/${document.id}/download-url`,
      );
      const anchor = window.document.createElement("a");
      anchor.href = downloadUrl;
      window.document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    } catch {
      // apiDownload already surfaced a toast.
    } finally {
      setDownloadingId(null);
    }
  }

  const selectedContract = contractsQuery.data?.find(({ id }) => id === contractId);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Document Vault
        </h1>
        <p className="mt-1 text-[13px] text-slate-500">
          Store agreements, MBs, bills, recovery memos, and PVC workbooks by contract.
        </p>
      </header>

      {contractsQuery.isLoading && (
        <div className="py-12 text-center text-[13px] text-slate-400">Loading contracts…</div>
      )}
      {contractsQuery.isError && (
        <ErrorPanel error={contractsQuery.error} fallback="Failed to load contracts" />
      )}
      {contractsQuery.data?.length === 0 && (
        <EmptyState
          icon={<FolderClosed className="h-4 w-4" strokeWidth={1.75} />}
          title="Create a contract first"
          description="Documents are stored against a contract so the audit trail stays unambiguous."
          action={
            <Link href="/contracts/new">
              <Button variant="primary">New contract</Button>
            </Link>
          }
        />
      )}

      {contractsQuery.data && contractsQuery.data.length > 0 && (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <label
              htmlFor="document-contract"
              className="block text-[11px] font-medium uppercase tracking-wider text-slate-500"
            >
              Contract
            </label>
            <select
              id="document-contract"
              value={contractId}
              disabled={upload.isPending}
              onChange={(event) => selectContract(event.target.value)}
              className="mt-2 h-9 w-full max-w-xl rounded-md border border-slate-300 bg-white px-3 text-[13px] text-slate-900 focus:border-amber-600 focus:outline-none"
            >
              <option value="">Select a contract…</option>
              {contractsQuery.data.map((contract) => (
                <option key={contract.id} value={contract.id}>
                  {contract.tender_number} — {contract.contractor_name}
                </option>
              ))}
            </select>
          </section>

          {!contractId && (
            <EmptyState
              icon={<FolderClosed className="h-4 w-4" strokeWidth={1.75} />}
              title="Select a contract"
              description="Choose the contract whose supporting documents you want to manage."
            />
          )}

          {contractId && (
            <>
              <UploadPanel
                contractLabel={selectedContract?.tender_number ?? "Selected contract"}
                fileType={fileType}
                file={file}
                fileError={fileError}
                isUploading={upload.isPending}
                mutationError={upload.error}
                fileInputRef={fileInputRef}
                onFileTypeChange={setFileType}
                onFileChange={chooseFile}
                onSubmit={submitUpload}
              />
              <DocumentList
                documents={documentsQuery.data}
                isLoading={documentsQuery.isLoading}
                error={documentsQuery.error}
                downloadingId={downloadingId}
                onDownload={download}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}

function UploadPanel({
  contractLabel,
  fileType,
  file,
  fileError,
  isUploading,
  mutationError,
  fileInputRef,
  onFileTypeChange,
  onFileChange,
  onSubmit,
}: {
  contractLabel: string;
  fileType: DocumentType;
  file: File | null;
  fileError: string | null;
  isUploading: boolean;
  mutationError: Error | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileTypeChange: (type: DocumentType) => void;
  onFileChange: (file: File | null) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-4">
        <h2 className="text-[15px] font-semibold text-slate-900">Upload document</h2>
        <p className="mt-1 text-[12px] text-slate-500">
          {contractLabel} · PDF or Excel · maximum 50 MB
        </p>
      </div>
      <form onSubmit={onSubmit} className="grid gap-4 md:grid-cols-[220px_1fr_auto] md:items-end">
        <label className="block text-[12px] font-medium text-slate-700">
          Document type
          <select
            value={fileType}
            disabled={isUploading}
            onChange={(event) => onFileTypeChange(event.target.value as DocumentType)}
            className="mt-1.5 h-9 w-full rounded-md border border-slate-300 bg-white px-3 text-[13px] focus:border-amber-600 focus:outline-none"
          >
            {DOCUMENT_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label className="block text-[12px] font-medium text-slate-700">
          File
          <input
            ref={fileInputRef}
            type="file"
            disabled={isUploading}
            accept=".pdf,.xls,.xlsx,.xlsm"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
            className="mt-1.5 block h-9 w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-[12px] text-slate-600 file:mr-3 file:border-0 file:bg-transparent file:text-[12px] file:font-medium file:text-slate-900"
          />
        </label>
        <Button type="submit" variant="primary" disabled={isUploading || !file || !!fileError}>
          <Upload className="h-3.5 w-3.5" strokeWidth={1.75} />
          {isUploading ? "Uploading…" : "Upload"}
        </Button>
      </form>
      {(fileError || mutationError) && (
        <p className="mt-3 text-[12px] text-red-600">
          {fileError ?? mutationError?.message}
        </p>
      )}
    </section>
  );
}

function DocumentList({
  documents,
  isLoading,
  error,
  downloadingId,
  onDownload,
}: {
  documents: VaultDocument[] | undefined;
  isLoading: boolean;
  error: Error | null;
  downloadingId: string | null;
  onDownload: (document: VaultDocument) => Promise<void>;
}) {
  if (isLoading) {
    return <div className="py-12 text-center text-[13px] text-slate-400">Loading documents…</div>;
  }
  if (error) return <ErrorPanel error={error} fallback="Failed to load documents" />;
  if (!documents?.length) {
    return (
      <EmptyState
        icon={<FolderClosed className="h-4 w-4" strokeWidth={1.75} />}
        title="No documents yet"
        description="Upload the first supporting file for this contract. Files are stored without parsing."
      />
    );
  }

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-3 text-[11px] font-medium uppercase tracking-wider text-slate-500">
        Documents
      </div>
      {documents.map((document, index) => (
        <div
          key={document.id}
          className={`flex items-center gap-4 px-5 py-3 ${
            index < documents.length - 1 ? "border-b border-slate-100" : ""
          }`}
        >
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-slate-200 text-slate-500">
            <FileText className="h-4 w-4" strokeWidth={1.75} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-medium text-slate-900">
              {document.original_filename}
            </p>
            <p className="mt-0.5 text-[12px] text-slate-500">
              {documentTypeLabel(document.file_type)} · {formatUploadedAt(document.uploaded_at)}
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={downloadingId === document.id}
            onClick={() => void onDownload(document)}
          >
            <Download className="h-3.5 w-3.5" strokeWidth={1.75} />
            {downloadingId === document.id ? "Downloading…" : "Download"}
          </Button>
        </div>
      ))}
    </section>
  );
}

function ErrorPanel({ error, fallback }: { error: unknown; fallback: string }) {
  return (
    <div className="rounded-xl border border-red-100 bg-red-50 px-5 py-4 text-[13px] text-red-600">
      {error instanceof Error ? error.message : fallback}
    </div>
  );
}

const uploadedAtFormatter = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatUploadedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return uploadedAtFormatter.format(date);
}
