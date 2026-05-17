export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-[400px]">
        <div className="mb-8 text-center">
          <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">RailPVC</h1>
          <p className="text-[13px] text-slate-500 mt-1">
            PVC billing OS for Indian Railway contractors
          </p>
        </div>
        {children}
      </div>
    </div>
  );
}
