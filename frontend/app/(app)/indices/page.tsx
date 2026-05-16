import { LineChart } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";

export default function IndicesPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Index Manager
        </h1>
        <p className="text-[13px] text-slate-500 mt-1">
          RBI WPI All-Commodities and JPC steel series by city. Seeded historical values
          plus monthly entry of current observations.
        </p>
      </header>

      <EmptyState
        icon={<LineChart className="h-4 w-4" strokeWidth={1.75} />}
        title="Index data not loaded yet"
        description="RBI + JPC seeds land alongside P3-006. Once API is live, this page will list series and let you add the current month."
      />
    </div>
  );
}
