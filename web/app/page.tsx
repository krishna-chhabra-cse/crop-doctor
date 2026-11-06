import Link from "next/link";
import { RESULTS as R } from "@/lib/results";

const pct = (x: number) => `${Math.round(x * 100)}%`;

function Stat({ value, label, note, tone = "brand" }: { value: string; label: string; note: string; tone?: "brand" | "red" }) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className={`text-4xl font-extrabold tracking-tight ${tone === "red" ? "text-red" : "text-brand"}`}>{value}</div>
      <div className="mt-1 font-semibold text-ink">{label}</div>
      <p className="mt-1 text-sm text-ink-3">{note}</p>
    </div>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="rounded-2xl border border-border bg-surface p-5">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft font-bold text-brand">{n}</div>
      <h3 className="mt-3 font-bold text-ink">{title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-ink-2">{children}</p>
    </li>
  );
}

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-4">
      <section className="pb-12 pt-12 sm:pt-20">
        <p className="inline-flex rounded-full bg-brand-soft px-3 py-1 text-sm font-semibold text-brand">
          Tomato &amp; potato leaf diseases
        </p>
        <h1 className="mt-4 max-w-3xl text-4xl font-extrabold leading-[1.1] tracking-tight text-ink sm:text-6xl">
          A crop doctor that knows when it doesn&apos;t know.
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-ink-2">
          Send a photo of a sick leaf. If the assistant is sure, it tells you the most likely disease, how urgent it is
          and what to do, with sources. If it isn&apos;t sure, it asks you one question or sends your photo to an
          expert instead of guessing.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link href="/check" className="rounded-2xl bg-brand px-6 py-4 text-center text-lg font-bold text-brand-ink shadow-sm hover:brightness-110">
            Check a leaf now
          </Link>
          <Link href="/check?sample=1" className="rounded-2xl border border-border bg-surface px-6 py-4 text-center text-lg font-semibold text-ink hover:bg-surface-2">
            Try with a sample photo
          </Link>
        </div>
      </section>

      <section aria-labelledby="how" className="pb-14">
        <h2 id="how" className="text-2xl font-bold text-ink">How it works</h2>
        <ol className="mt-5 grid gap-4 sm:grid-cols-3">
          <Step n={1} title="Photo of one leaf">
            Choose tomato or potato and take a photo in daylight. A quick check asks you to retake blurry or dark photos.
          </Step>
          <Step n={2} title="An honest answer">
            You get a short list of possible diseases that contains the right one about {pct(R.coverageTarget)} of the time.
            One disease means a clear answer; two or three means one quick question.
          </Step>
          <Step n={3} title="An expert when unsure">
            Unclear photos go to an agriculture expert. Every checked answer makes the assistant&apos;s confidence more
            accurate straight away.
          </Step>
        </ol>
      </section>

      <section aria-labelledby="why" className="pb-14">
        <h2 id="why" className="text-2xl font-bold text-ink">Why honesty matters</h2>
        <p className="mt-2 max-w-2xl text-ink-2">
          Measured on {R.fieldTestPhotos} real farm photos that none of the models saw during training.
        </p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat tone="red" value={pct(R.labOnlyFieldAccuracy)} label="A typical lab-trained model"
            note={`${pct(R.labAccuracy)} right on lab photos, but only ${pct(R.labOnlyFieldAccuracy)} on farm photos, while ${pct(R.labOnlyFieldConfidence)} sure of itself.`} />
          <Stat value={pct(R.finalFieldAccuracy)} label="Our model's top answer"
            note="Trained on lab and real field photos, and it knows which crop you're photographing." />
          <Stat value={pct(R.coverage)} label="Shortlist contains the right disease"
            note={`Target ${pct(R.coverageTarget)}; on average ${R.avgShortlist.toFixed(1)} diseases in the shortlist.`} />
          <Stat value={pct(R.accuracyWhenAnswered)} label="Right when it answers alone"
            note={`It answers about ${pct(R.answeredByAssistant)} of photos itself and sends the rest to an expert.`} />
        </div>
      </section>

      <section className="mb-16 rounded-3xl bg-brand px-6 py-10 text-brand-ink sm:px-10">
        <h2 className="text-2xl font-bold">Try it on your own plants</h2>
        <p className="mt-2 max-w-xl opacity-90">
          Works on any phone browser. No app to install. The advice always ends with a reminder to check with your local
          agriculture officer before spraying.
        </p>
        <Link href="/check" className="mt-6 inline-block rounded-2xl bg-white px-6 py-3 font-bold text-brand hover:bg-brand-soft">
          Check a leaf
        </Link>
      </section>
    </div>
  );
}
