import Link from "next/link";

const POINTS = [
  {
    title: "Explicit W derivation",
    body: "Cement, steel and exclusions are named steps — never silent defaults.",
  },
  {
    title: "Rolling quarters from base month",
    body: "The correct three-month index window for every bill, automatically.",
  },
  {
    title: "Immutable approved runs",
    body: "Corrections supersede — the audit trail never rewrites itself.",
  },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* ─── Brand panel (desktop only) ─── */}
      <aside className="hidden lg:flex w-[44%] max-w-[560px] bg-slate-900 text-white flex-col justify-between p-10 xl:p-14">
        <Link
          href="/"
          className="text-[17px] font-semibold tracking-tight text-white hover:text-slate-200 transition-colors w-fit"
        >
          TenderAudit
        </Link>

        <div>
          <p className="text-[12px] font-medium tracking-wide uppercase text-amber-500 mb-4">
            PVC billing OS · GCC Clause 46A
          </p>
          <h2 className="text-[26px] xl:text-[30px] leading-[1.2] font-semibold tracking-tight">
            Price variation bills that survive audit.
          </h2>
          <ul className="mt-8 space-y-5">
            {POINTS.map((p) => (
              <li key={p.title} className="flex gap-3">
                <span
                  aria-hidden
                  className="mt-[7px] h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0"
                />
                <div>
                  <p className="text-[13.5px] font-medium text-slate-100">{p.title}</p>
                  <p className="text-[12.5px] text-slate-400 mt-0.5">{p.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="num-mono text-[12px] text-slate-500">
          Verified to the paisa against real submitted PVC workbooks.
        </p>
      </aside>

      {/* ─── Form panel ─── */}
      <main className="flex-1 bg-white flex flex-col">
        {/* Compact brand header for mobile */}
        <div className="lg:hidden px-6 pt-6">
          <Link href="/" className="text-[16px] font-semibold tracking-tight text-slate-900">
            TenderAudit
          </Link>
        </div>

        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="w-full max-w-[380px]">{children}</div>
        </div>

        <p className="lg:hidden px-6 pb-6 text-center text-[11px] text-slate-400">
          PVC billing OS for Indian Railway contractors
        </p>
      </main>
    </div>
  );
}
