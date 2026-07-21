"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { apiFetch } from "@/lib/api/client";
import { ContractForm } from "@/components/contracts/ContractForm";
import type { ContractFormValues } from "@/lib/contracts-schema";
import {
  JourneyGuide,
  PageGuidance,
} from "@/components/help/FirstUserHelp";
import { CONTRACT_SETUP_GUIDANCE } from "@/lib/firstUserHelp";

type CreatedContract = { id: string };

export default function NewContractPage() {
  const router = useRouter();

  async function onSubmit(values: ContractFormValues) {
    const created = await apiFetch<CreatedContract>("/api/contracts", {
      method: "POST",
      body: values,
    });
    router.push(`/contracts/${created.id}`);
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <header className="space-y-2">
        <Link
          href="/contracts"
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Contracts
        </Link>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          New contract
        </h1>
        <p className="text-[13px] text-slate-500">
          Creates a Draft contract. You can keep configuring schedules and items
          on the detail page after this step.
        </p>
      </header>

      <JourneyGuide stage="contract" />
      <PageGuidance
        title="Set the calculation foundation"
        next="Create schedules and add or import the agreement items."
      >
        {CONTRACT_SETUP_GUIDANCE} Check every value against the signed
        agreement; it remains editable while the contract is a draft.
      </PageGuidance>

      <ContractForm onSubmit={onSubmit} submitLabel="Create contract" />
    </div>
  );
}
