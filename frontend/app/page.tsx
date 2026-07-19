import Link from "next/link";

/* Public marketing landing page. Logged-in users never see this —
   proxy.ts redirects them from "/" to /contracts. */

const FEATURES = [
  {
    title: "Deterministic PVC engine",
    body: "Component-wise Clause 46A calculation with fixed rounding rules. The same inputs always produce the same paisa — verified against real submitted workbooks.",
  },
  {
    title: "Explicit W derivation",
    body: "Cement, steel buckets, technical withheld and extra-item exclusions are named, confirmed steps. A run blocks on a missing decision — it never assumes.",
  },
  {
    title: "Rolling quarters, done right",
    body: "Quarters anchor to the contract's base month, not the calendar. Index averages use the correct three-month window for every bill's measurement date.",
  },
  {
    title: "Immutable approved runs",
    body: "An approved run is frozen with its inputs snapshotted. Corrections create a superseding run — the audit trail never rewrites itself.",
  },
  {
    title: "Excel-parity export",
    body: "The export matches the submission format Railway field accounts already expect — native numeric cells, live totals, familiar column order.",
  },
  {
    title: "Seeded index master",
    body: "RBI and JPC index history since 2022 is pre-loaded. Add each new month once and every affected contract picks it up.",
  },
];

const STEPS = [
  {
    n: "01",
    title: "Set up the contract",
    body: "Agreement, LOA, base month, schedules, component weights and the applicable GCC clause — captured once, validated up front.",
  },
  {
    n: "02",
    title: "Enter bills and recoveries",
    body: "Running bills, recovery sheets and monthly indices go in as structured data with carry-forward handled automatically.",
  },
  {
    n: "03",
    title: "Run, approve, export",
    body: "The engine computes the claim, a reviewer approves it, and you export the submission pack — every number traceable to its source.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      {/* ─── Nav ─── */}
      <header className="border-b border-slate-100">
        <div className="mx-auto max-w-6xl px-6 h-16 flex items-center justify-between">
          <span className="text-[16px] font-semibold tracking-tight">
            TenderAudit
          </span>
          <nav className="flex items-center gap-2">
            <Link
              href="/login"
              className="px-3.5 h-9 inline-flex items-center text-[13px] font-medium text-slate-600 hover:text-slate-900 transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className="px-4 h-9 inline-flex items-center rounded-lg bg-slate-900 text-white text-[13px] font-medium hover:bg-slate-800 transition-colors"
            >
              Get started
            </Link>
          </nav>
        </div>
      </header>

      {/* ─── Hero ─── */}
      <section className="mx-auto max-w-6xl px-6 pt-20 pb-16 lg:pt-28 lg:pb-24 grid lg:grid-cols-2 gap-14 items-center">
        <div>
          <p className="text-[12px] font-medium tracking-wide uppercase text-amber-600 mb-4">
            PVC billing for Indian Railway contractors
          </p>
          <h1 className="text-[34px] lg:text-[42px] leading-[1.1] font-semibold tracking-tight text-slate-900">
            Price variation bills that survive audit.
          </h1>
          <p className="mt-5 text-[15px] leading-relaxed text-slate-600 max-w-[48ch]">
            TenderAudit turns your agreements, running bills and published
            RBI/JPC indices into deterministic, audit-ready PVC claims under
            GCC Clause 46A — replacing the fragile Excel workbooks your
            billing depends on today.
          </p>
          <div className="mt-8 flex items-center gap-3">
            <Link
              href="/signup"
              className="px-5 h-10 inline-flex items-center rounded-lg bg-slate-900 text-white text-[13px] font-medium hover:bg-slate-800 transition-colors"
            >
              Create your account
            </Link>
            <Link
              href="/login"
              className="px-5 h-10 inline-flex items-center rounded-lg border border-slate-200 text-[13px] font-medium text-slate-700 hover:border-slate-300 hover:bg-slate-50 transition-colors"
            >
              Sign in
            </Link>
          </div>
          <p className="mt-6 text-[12px] text-slate-400">
            Verified to the paisa against real submitted PVC workbooks.
          </p>
        </div>

        {/* Stylized PVC-run card */}
        <div className="relative">
          <div className="absolute -inset-6 bg-gradient-to-tr from-slate-50 via-amber-50/60 to-slate-50 rounded-3xl -z-10" />
          <div className="bg-white border border-slate-200 rounded-xl shadow-[0_12px_32px_rgba(15,23,42,0.08)] overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
              <span className="text-[12px] font-medium text-slate-700">
                PVC Run — CA-2023-WR-114 · Bill 7
              </span>
              <span className="text-[11px] font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
                Approved
              </span>
            </div>
            <div className="px-5 py-4 space-y-2.5 num-mono text-[12.5px]">
              <Row label="On-account bill (gross)" value="1,84,62,410.00" />
              <Row label="− Cement" value="12,08,330.00" muted />
              <Row label="− Steel · angles / plates / other" value="21,44,105.00" muted />
              <Row label="− Technical withheld" value="3,50,000.00" muted />
              <Row label="− Excluded extra items" value="1,86,240.00" muted />
              <div className="border-t border-slate-100 pt-2.5">
                <Row label="W — eligible base" value="1,45,73,735.00" strong />
              </div>
              <Row label="Quarter (rolling, base Mar-2023)" value="Q13" plain />
              <Row label="Index avg (M−2 · M−1 · M)" value="382.4667" plain />
              <div className="border-t border-slate-100 pt-2.5">
                <div className="flex items-baseline justify-between">
                  <span className="font-sans text-[12px] font-medium text-slate-700">
                    PVC payable this bill
                  </span>
                  <span className="text-[15px] font-semibold text-amber-700">
                    ₹ 6,38,412.00
                  </span>
                </div>
              </div>
            </div>
            <div className="px-5 py-2.5 bg-slate-50 border-t border-slate-100 text-[11px] text-slate-400 font-sans">
              Every figure traceable to its source bill line and published index.
            </div>
          </div>
        </div>
      </section>

      {/* ─── Stat strip ─── */}
      <section className="border-y border-slate-100 bg-slate-50/60">
        <div className="mx-auto max-w-6xl px-6 py-10 grid grid-cols-1 sm:grid-cols-3 gap-8 text-center">
          <Stat big="4–8 hrs → minutes" small="per PVC bill, from transcription and averaging to export" />
          <Stat big="Zero silent defaults" small="runs block on missing eligibility decisions instead of guessing" />
          <Stat big="Clause 46A native" small="GCC price variation rules encoded, not re-derived per engineer" />
        </div>
      </section>

      {/* ─── Features ─── */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="text-[24px] font-semibold tracking-tight text-slate-900">
          Built for the way Railway billing actually works
        </h2>
        <p className="mt-2 text-[14px] text-slate-500 max-w-[60ch]">
          Not a generic invoicing tool — a vertical billing OS for the PVC
          chain: agreement, schedules, MB, running bills, recoveries, indices.
        </p>
        <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-slate-100 border border-slate-100 rounded-xl overflow-hidden">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-white p-6">
              <h3 className="text-[14px] font-semibold text-slate-900">
                {f.title}
              </h3>
              <p className="mt-2 text-[13px] leading-relaxed text-slate-500">
                {f.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── How it works ─── */}
      <section className="border-t border-slate-100 bg-slate-50/60">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="text-[24px] font-semibold tracking-tight text-slate-900">
            From contract file to submission pack
          </h2>
          <div className="mt-10 grid md:grid-cols-3 gap-8">
            {STEPS.map((s) => (
              <div key={s.n}>
                <span className="num-mono text-[13px] text-amber-600">{s.n}</span>
                <h3 className="mt-2 text-[15px] font-semibold text-slate-900">
                  {s.title}
                </h3>
                <p className="mt-2 text-[13px] leading-relaxed text-slate-500">
                  {s.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="mx-auto max-w-6xl px-6 py-20 text-center">
        <h2 className="text-[26px] font-semibold tracking-tight text-slate-900">
          Stop rebuilding the same workbook every quarter.
        </h2>
        <p className="mt-3 text-[14px] text-slate-500 max-w-[52ch] mx-auto">
          Set up a contract once and every PVC bill after that is computed,
          reviewed and exported from the same auditable source of truth.
        </p>
        <Link
          href="/signup"
          className="mt-8 px-6 h-11 inline-flex items-center rounded-lg bg-slate-900 text-white text-[14px] font-medium hover:bg-slate-800 transition-colors"
        >
          Get started free
        </Link>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-slate-100">
        <div className="mx-auto max-w-6xl px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-[12px] text-slate-400">
            © {new Date().getFullYear()} TenderAudit · PVC billing OS for
            Indian Railway contractors
          </span>
          <div className="flex items-center gap-5 text-[12px] text-slate-500">
            <Link href="/login" className="hover:text-slate-900 transition-colors">
              Sign in
            </Link>
            <Link href="/signup" className="hover:text-slate-900 transition-colors">
              Create account
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Row({
  label,
  value,
  muted,
  strong,
  plain,
}: {
  label: string;
  value: string;
  muted?: boolean;
  strong?: boolean;
  plain?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span
        className={`font-sans text-[12px] ${
          strong ? "font-medium text-slate-700" : "text-slate-500"
        }`}
      >
        {label}
      </span>
      <span
        className={
          strong
            ? "font-semibold text-slate-900"
            : muted
              ? "text-slate-400"
              : plain
                ? "text-slate-500"
                : "text-slate-700"
        }
      >
        {value}
      </span>
    </div>
  );
}

function Stat({ big, small }: { big: string; small: string }) {
  return (
    <div>
      <p className="text-[18px] font-semibold tracking-tight text-slate-900">
        {big}
      </p>
      <p className="mt-1 text-[12px] text-slate-500 max-w-[32ch] mx-auto">
        {small}
      </p>
    </div>
  );
}
