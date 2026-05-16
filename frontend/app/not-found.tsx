import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="min-h-screen grid place-items-center bg-slate-50 px-6">
      <div className="max-w-md w-full bg-white border border-slate-200 rounded-xl p-6 text-center">
        <span className="mx-auto grid place-items-center h-10 w-10 rounded-lg border border-slate-200 text-slate-500">
          <FileQuestion className="h-4 w-4" strokeWidth={1.75} />
        </span>
        <h1 className="mt-3 text-[16px] font-semibold text-slate-900">
          Page not found.
        </h1>
        <p className="mt-1 text-[13px] text-slate-500">
          The URL doesn&apos;t match anything in RailPVC.
        </p>
        <div className="mt-4">
          <Link href="/contracts">
            <Button variant="primary">Back to Contracts</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
