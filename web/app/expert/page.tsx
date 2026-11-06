import type { Metadata } from "next";
import ExpertDashboard from "@/components/expert/ExpertDashboard";

export const metadata: Metadata = { title: "Expert dashboard" };

export default function ExpertPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 pb-20 pt-6">
      <ExpertDashboard />
    </div>
  );
}
