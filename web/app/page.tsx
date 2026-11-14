"use client";

// Landing page, built with the immersive-concept method: one axis, FIELD (−1) ⟷ MODEL (+1).
// The concept block is at the top of app/immersive.css; the engine is components/immersive/useHeroEngine.ts.
import Link from "next/link";
import { useRef } from "react";
import { useT } from "@/lib/i18n";
import { RESULTS as R } from "@/lib/results";
import { DEFS, POLE_A, POLE_B, UNDER_A, UNDER_B, PAPER } from "@/components/immersive/heroArt.generated";
import { useHeroEngine } from "@/components/immersive/useHeroEngine";
import { fraunces, plexMono, tiro } from "@/components/immersive/fonts";
import "./immersive.css";

// Round DOWN so a result is never overstated (99.5% shows as 99%, not 100%).
const pct = (x: number) => `${Math.floor(x * 100 + 1e-9)}%`;

const COPY = {
  en: {
    h1: "Crop Doctor: a crop disease assistant that answers when it is sure and asks an expert when it isn't",
    capsA: ["Your leaf", "Your field"],
    capsB: ["The model", "Its doubt"],
    tagline: ["Where your ", "field", " and the ", "model", " meet, and it tells you when it isn't sure."],
    meta: `Tomato & potato · English & हिंदी · tested on ${R.fieldTestPhotos.toLocaleString("en-IN")} field photos`,
    check: "Check a leaf",
    numbers: "See the numbers",
    cue: "↓ Scroll",
    s01: "The idea",
    ideaText:
      "A photo of a leaf in a real field looks nothing like the clean lab photos most models learn from. Crop Doctor is built for that gap. It answers when it is sure, asks you one question when it is almost sure, and sends your photo to a person when it is not.",
    cropTitle: "Crop",
    cropTag: "what you see",
    cropText: "Your photo, taken in sun or shade, with soil, shadows and other leaves in it. That is what the model has to read.",
    docTitle: "Doctor",
    docTag: "what it knows, and what it doesn't",
    docText: "Trained on lab photos, tested on field photos, and measured on how often its doubt is right, not only how often it is.",
    s1x: "§1.1 How it works",
    howTitle: "One leaf, one answer, or an honest “not sure”.",
    steps: [
      ["Photograph one leaf", "In daylight, the sick leaf filling most of the frame."],
      ["Get an answer, or one question", "If two diseases look alike, it shows both and asks which matches your leaf."],
      ["Not sure? A person answers", "Your photo goes to an expert's queue, and their answer comes back in the app."],
    ],
    figCaption: "A potato leaf from a field. Crop Doctor's answer: early blight.",
    s02a: "§02 For farmers",
    s02aTitle: "What happens when you send a photo",
    pathA: [
      ["§2.1", "It is sure", "You get the disease, what causes it, and what to do this week, in English or Hindi."],
      ["§2.2", "It is almost sure", "It shows the two diseases it is torn between and asks which looks like your leaf."],
      ["§2.3", "It is not sure", "It says so. Your photo goes to an expert, and you are told to confirm with your KVK."],
    ],
    sayA: "It never guesses to sound clever.",
    s02b: "§02 For the curious",
    s02bTitle: "The numbers, the hard one first",
    pathB: [
      ["§2.1", pct(R.labOnlyFieldAccuracy), `A model trained only on lab photos, tested on field photos. It was confident ${pct(R.labOnlyFieldConfidence)} of the time anyway.`],
      ["§2.2", pct(R.plantdocAccuracy), "Our first answer on PlantDoc field photos, the hardest public test set."],
      ["§2.3", pct(R.coverage), `of the time the true disease is in the shortlist it shows. The target was ${pct(R.coverageTarget)}.`],
      ["§2.4", pct(R.accuracyWhenAnswered), `right when it answers on its own, which it does for ${pct(R.answeredByAssistant)} of photos. The rest go to a person.`],
    ],
    sayB: "We headline the hard number, not the flattering one.",
    s03: "§03 Try it",
    closeTitle: "Have a sick leaf? Photograph it.",
    closeText: "No account. Works on a cheap phone. If it can't tell, it will say so.",
    expertTitle: "Are you an agronomist?",
    expertText: "The photos it was not sure about wait in a queue for someone who knows.",
    expertLink: "Open the expert queue",
    chatTitle: "Have a question, not a photo?",
    chatText: "Ask in plain words after a check, and it answers only from what it knows.",
    chatLink: "Start with a leaf",
  },
  hi: {
    h1: "क्रॉप डॉक्टर: फ़सल रोग सहायक जो पक्का होने पर जवाब देता है और पक्का न होने पर विशेषज्ञ से पूछता है",
    capsA: ["आपका पत्ता", "आपका खेत"],
    capsB: ["मॉडल", "उसका संदेह"],
    tagline: ["जहाँ आपका ", "खेत", " और ", "मॉडल", " मिलते हैं, और पक्का न हो तो वह साफ़ बताता है।"],
    meta: `टमाटर और आलू · हिंदी और English · ${R.fieldTestPhotos.toLocaleString("en-IN")} खेत की फ़ोटो पर परखा`,
    check: "पत्ता जाँचें",
    numbers: "आँकड़े देखें",
    cue: "↓ स्क्रॉल करें",
    s01: "विचार",
    ideaText:
      "खेत में ली गई पत्ते की फ़ोटो उन साफ़ लैब फ़ोटो जैसी बिल्कुल नहीं होती जिनसे ज़्यादातर मॉडल सीखते हैं। क्रॉप डॉक्टर इसी अंतर के लिए बना है। पक्का होने पर जवाब देता है, लगभग पक्का होने पर एक सवाल पूछता है, और पक्का न होने पर आपकी फ़ोटो किसी व्यक्ति को भेजता है।",
    cropTitle: "फ़सल",
    cropTag: "जो आप देखते हैं",
    cropText: "धूप या छाँव में ली गई आपकी फ़ोटो, जिसमें मिट्टी, परछाईं और दूसरे पत्ते भी हैं। मॉडल को यही पढ़ना होता है।",
    docTitle: "डॉक्टर",
    docTag: "जो वह जानता है, और जो नहीं",
    docText: "लैब फ़ोटो पर सिखाया, खेत की फ़ोटो पर परखा, और यह भी मापा कि उसका संदेह कितनी बार सही होता है।",
    s1x: "§1.1 यह कैसे काम करता है",
    howTitle: "एक पत्ता, एक जवाब, या ईमानदार “पक्का नहीं”।",
    steps: [
      ["एक पत्ते की फ़ोटो लें", "दिन की रोशनी में, बीमार पत्ता फ़्रेम का ज़्यादातर हिस्सा भरे।"],
      ["जवाब पाएँ, या एक सवाल", "अगर दो रोग एक जैसे दिखें, तो दोनों दिखाकर पूछता है कि आपका पत्ता किससे मिलता है।"],
      ["पक्का नहीं? कोई व्यक्ति जवाब देगा", "आपकी फ़ोटो विशेषज्ञ की कतार में जाती है, और उनका जवाब ऐप में आता है।"],
    ],
    figCaption: "खेत से आलू का पत्ता। क्रॉप डॉक्टर का जवाब: अगेती झुलसा।",
    s02a: "§02 किसानों के लिए",
    s02aTitle: "फ़ोटो भेजने पर क्या होता है",
    pathA: [
      ["§2.1", "वह पक्का है", "आपको रोग, उसका कारण, और इस हफ़्ते क्या करना है, हिंदी या अंग्रेज़ी में मिलता है।"],
      ["§2.2", "वह लगभग पक्का है", "जिन दो रोगों में उलझा है, उन्हें दिखाकर पूछता है कि कौन-सा आपके पत्ते जैसा है।"],
      ["§2.3", "वह पक्का नहीं है", "वह यह साफ़ कहता है। फ़ोटो विशेषज्ञ को जाती है, और आपको KVK से पुष्टि करने को कहा जाता है।"],
    ],
    sayA: "वह होशियार दिखने के लिए अंदाज़ा नहीं लगाता।",
    s02b: "§02 जिज्ञासुओं के लिए",
    s02bTitle: "आँकड़े, सबसे कठिन पहले",
    pathB: [
      ["§2.1", pct(R.labOnlyFieldAccuracy), `सिर्फ़ लैब फ़ोटो पर सिखाया मॉडल, खेत की फ़ोटो पर। फिर भी ${pct(R.labOnlyFieldConfidence)} बार वह आश्वस्त था।`],
      ["§2.2", pct(R.plantdocAccuracy), "PlantDoc खेत फ़ोटो पर हमारा पहला जवाब, सबसे कठिन सार्वजनिक परीक्षण।"],
      ["§2.3", pct(R.coverage), `बार सही रोग उसकी छोटी सूची में होता है। लक्ष्य ${pct(R.coverageTarget)} था।`],
      ["§2.4", pct(R.accuracyWhenAnswered), `सही, जब वह ख़ुद जवाब देता है, जो ${pct(R.answeredByAssistant)} फ़ोटो पर होता है। बाकी किसी व्यक्ति को जाती हैं।`],
    ],
    sayB: "हम कठिन आँकड़ा सबसे आगे रखते हैं, लुभावना नहीं।",
    s03: "§03 आज़माएँ",
    closeTitle: "बीमार पत्ता है? उसकी फ़ोटो लें।",
    closeText: "कोई खाता नहीं। सस्ते फ़ोन पर भी चलता है। पहचान न सके तो साफ़ बताएगा।",
    expertTitle: "क्या आप कृषि विशेषज्ञ हैं?",
    expertText: "जिन फ़ोटो पर वह पक्का नहीं था, वे किसी जानकार के इंतज़ार में कतार में हैं।",
    expertLink: "विशेषज्ञ कतार खोलें",
    chatTitle: "फ़ोटो नहीं, सवाल है?",
    chatText: "जाँच के बाद सीधे शब्दों में पूछें; वह सिर्फ़ उसी से जवाब देता है जो वह जानता है।",
    chatLink: "एक पत्ते से शुरू करें",
  },
};

function HeroArt() {
  return (
    <div className="im-art" aria-hidden="true">
      <svg className="im-under im-under--a" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" dangerouslySetInnerHTML={{ __html: UNDER_A }} />
      <svg className="im-under im-under--b" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" dangerouslySetInnerHTML={{ __html: UNDER_B }} />
      <svg className="im-art__main" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
        <defs dangerouslySetInnerHTML={{ __html: DEFS +
          `<filter id="cd-soft"><feGaussianBlur stdDeviation="3"/></filter>` +
          `<mask id="cd-mask-a" maskUnits="userSpaceOnUse" x="-200" y="0" width="2000" height="900"><rect x="-200" width="2000" height="900" fill="#fff"/><g id="cd-cells-a" fill="#000" filter="url(#cd-soft)"></g></mask>` +
          `<mask id="cd-mask-b" maskUnits="userSpaceOnUse" x="-200" y="0" width="2000" height="900"><rect x="-200" width="2000" height="900" fill="#fff"/><g id="cd-cells-b" fill="#000" shape-rendering="crispEdges"></g></mask>` +
          `<clipPath id="cd-clip-a"><rect x="-200" width="1000" height="900"/></clipPath>` +
          `<clipPath id="cd-clip-b"><rect x="800" width="1000" height="900"/></clipPath>` }} />
        <rect width="1600" height="900" fill={PAPER} />
        <g mask="url(#cd-mask-b)"><g id="cd-pole-b" dangerouslySetInnerHTML={{ __html: POLE_B }} /></g>
        <g mask="url(#cd-mask-a)"><g id="cd-pole-a" dangerouslySetInnerHTML={{ __html: POLE_A }} /></g>
      </svg>
      <canvas className="im-particles" />
    </div>
  );
}

const serif = "[font-family:var(--serif)] text-[1.375rem] font-normal text-[var(--ink)]";

export default function Home() {
  const t = useT();
  const c = t.hi ? COPY.hi : COPY.en;
  const root = useRef<HTMLDivElement>(null);
  useHeroEngine(root);

  return (
    <div ref={root} className={`im im-path-a ${fraunces.variable} ${tiro.variable} ${plexMono.variable}`}>
      <section className="im-hero" aria-labelledby="im-h1">
        <h1 id="im-h1" className="sr-only">{c.h1}</h1>
        <HeroArt />
        <div className="im-stage">
          <div className="im-logo" aria-hidden="true">
            <span className="word word--a">Crop</span>
            <span className="ring" />
            <span className="word word--b">Doctor</span>
          </div>
          <div className="im-caps im-caps--a" aria-hidden="true">{c.capsA.map((w) => <span key={w}>{w}</span>)}</div>
          <div className="im-caps im-caps--b" aria-hidden="true">{c.capsB.map((w) => <span key={w}>{w}</span>)}</div>
          <div className="im-plumb" aria-hidden="true" />
          <div className="im-foot">
            <p className="tagline">
              {c.tagline[0]}<em className="acc-a">{c.tagline[1]}</em>{c.tagline[2]}<em className="acc-b">{c.tagline[3]}</em>{c.tagline[4]}
            </p>
            <div className="im-cta">
              <Link href="/check" className="btn btn--primary">{c.check}</Link>
              <a href="#numbers" className="btn btn--secondary">{c.numbers}</a>
            </div>
            <p className="im-meta">{c.meta}</p>
            <p className="im-cue">{c.cue}</p>
          </div>
        </div>
      </section>

      <div className="im-body">
        <div className="im-col">
          <section className="im-sec" aria-labelledby="im-idea">
            <p className="num"><b>§01</b> {c.s01}</p>
            <h2 id="im-idea" className="im-idea-h">
              <span className="acc-a">{c.cropTitle}</span><span className="plus">+</span><span className="acc-b">{c.docTitle}</span>
            </h2>
            <p>{c.ideaText}</p>
            <div className="im-pair">
              <div className="panel panel--a">
                <h3 className="acc-a">{c.cropTitle}</h3>
                <p className="tagline">{c.cropTag}</p>
                <p className="mt-3">{c.cropText}</p>
              </div>
              <div className="panel panel--b">
                <h3 className="acc-b">{c.docTitle}</h3>
                <p className="tagline">{c.docTag}</p>
                <p className="mt-3">{c.docText}</p>
              </div>
            </div>
          </section>

          <section className="im-sec" aria-labelledby="im-how">
            <p className="eyebrow">{c.s1x}</p>
            <h2 id="im-how">{c.howTitle}</h2>
            <div className="im-how grid gap-6">
              <ol className="im-steps">
                {c.steps.map(([h, d], i) => (
                  <li key={h}>
                    <span className="num"><b>{`0${i + 1}`}</b></span>
                    <strong>{h}</strong>
                    <span>{d}</span>
                  </li>
                ))}
              </ol>
              <figure className="figure">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/landing/diag_potato.jpg" alt={c.figCaption} width={800} height={615} loading="lazy" />
                <figcaption>{c.figCaption}</figcaption>
              </figure>
            </div>
          </section>

          <div className="im-paths" id="numbers">
            <section className="im-path im-path--a" aria-labelledby="im-pa">
              <p className="eyebrow eyebrow--a">{c.s02a}</p>
              <h2 id="im-pa">{c.s02aTitle}</h2>
              <ol>
                {c.pathA.map(([n, h, d]) => (
                  <li key={n}>
                    <span className="num"><b>{n}</b></span>
                    <strong className={serif}>{h}</strong>
                    <span>{d}</span>
                  </li>
                ))}
              </ol>
              <p className="say">{c.sayA}</p>
            </section>
            <section className="im-path im-path--b" aria-labelledby="im-pb">
              <p className="eyebrow eyebrow--b">{c.s02b}</p>
              <h2 id="im-pb">{c.s02bTitle}</h2>
              <ol>
                {c.pathB.map(([n, big, d]) => (
                  <li key={n}>
                    <span className="num"><b>{n}</b></span>
                    <span className="im-big">{big}</span>
                    <span>{d}</span>
                  </li>
                ))}
              </ol>
              <p className="say">{c.sayB}</p>
            </section>
          </div>

          <section className="im-sec im-close" aria-labelledby="im-close">
            <p className="eyebrow">{c.s03}</p>
            <h2 id="im-close">{c.closeTitle}</h2>
            <p>{c.closeText}</p>
            <div><Link href="/check" className="btn btn--primary">{c.check}</Link></div>
          </section>

          <div className="im-more">
            <div className="panel panel--b">
              <h3 className="text-[1.4rem]">{c.expertTitle}</h3>
              <p className="mt-2">{c.expertText}</p>
              <p className="mt-4"><Link href="/expert">{c.expertLink}</Link></p>
            </div>
            <div className="panel panel--a">
              <h3 className="text-[1.4rem]">{c.chatTitle}</h3>
              <p className="mt-2">{c.chatText}</p>
              <p className="mt-4"><Link href="/check">{c.chatLink}</Link></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
