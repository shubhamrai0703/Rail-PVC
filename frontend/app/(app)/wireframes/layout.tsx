import { notFound } from "next/navigation";
import Link from "next/link";
import { FlaskConical } from "lucide-react";

/**
 * Dev-only wireframe area.
 *
 * These routes are design artefacts fed by static fixtures — no API calls, no
 * writes, no real data. They are excluded from production builds by the guard
 * below, which renders the standard 404 rather than the wireframe tree.
 *
 * Note on the folder name: the handoff suggested `_wireframes/`, but an
 * underscore prefix makes a folder *private* in the App Router — it and every
 * subfolder are opted out of routing entirely, so the screens would not have
 * been reachable at any URL. `wireframes/` + this runtime guard achieves the
 * "dev-only" intent while keeping the screens navigable, which the definition
 * of done requires.
 */
export default function WireframesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-violet-200 bg-violet-50 px-4 py-2.5">
        <div className="flex items-center gap-2 text-[12px] text-violet-900">
          <FlaskConical className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
          <span>
            <span className="font-medium">Wireframe — fixture data, dev builds only.</span>{" "}
            Nothing here is saved and no number on these screens is real.
          </span>
        </div>
        <Link
          href="/wireframes"
          className="text-[12px] text-violet-800 underline decoration-violet-300 underline-offset-2 hover:text-violet-950"
        >
          All wireframes
        </Link>
      </div>
      {children}
    </div>
  );
}
