import type { Metadata } from "next";
import { Suspense } from "react";
import CheckFlow, { CheckLoading } from "@/components/check/CheckFlow";

export const metadata: Metadata = { title: "Check a leaf" };

export default function CheckPage() {
  // CheckFlow reads ?case= and ?sample= from the URL, so it renders on the client inside Suspense.
  return (
    <div className="mx-auto max-w-2xl px-4 pb-24 pt-6">
      <Suspense fallback={<CheckLoading />}>
        <CheckFlow />
      </Suspense>
    </div>
  );
}
