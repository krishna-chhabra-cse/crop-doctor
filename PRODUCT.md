# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
- **Primary:** Indian smallholder tomato and potato farmers. They use cheap Android phones, often on slow mobile data and outdoors in daylight, and read Hindi or English. Their job: photograph a sick leaf and learn what it is and what to do, without being misled.
- **Secondary:** course examiners and the viva panel, who judge whether the project's research claims are honest and well supported.
- **Experts:** agriculture experts who review the photos the model is unsure about (`/expert`).

## Product Purpose
Crop Doctor is a student ML project. A farmer photographs one tomato or potato leaf. The model answers only when it is sure, asks one tap-to-answer question when it is almost sure, and otherwise sends the photo to a human expert instead of guessing. After an answer, the farmer can chat; the language model only rephrases the verified answer and never invents a diagnosis. Success means farmers get a trustworthy answer or an honest "not sure", never a confident wrong one.

## Positioning
Most plant-disease apps give an answer for every photo. Crop Doctor's difference is measured honesty under real field conditions. A typical lab-trained model is 98% right on lab photos but 25% on field photos while 83% sure of itself. Crop Doctor uses conformal prediction to keep the true disease on its shortlist 90% of the time, checked per type of photo, and hands uncertain cases to a person.

## Operating Context
- Routes: `/` landing page, `/check` farmer flow (photo, answer, follow-up question, expert hand-off, chat), `/expert` expert dashboard.
- The Python API sleeps when idle and takes about a minute to wake; the site pings it on load.
- Replies can come in 8 Indian languages; the screens are in English and Hindi.

## Capabilities and Constraints
- Crops: tomato and potato only (11 classes, plus an "something else" class for unknown problems).
- Three answer types: Sure, Almost sure (one question), Not sure (expert). Blurry or dark photos are asked to be retaken.
- Stack: Next.js 16 + Tailwind v4 frontend (`web/`), FastAPI backend (`server/`).
- Not yet available: a clean, unwatermarked field photo the model is confirmed to send to an expert.

## Brand Commitments
- **Honest numbers rule:** lead with the hard numbers (25% on field photos for a lab-only model, 63% first answer right on varied farm photos, the 90% shortlist promise). Never headline the 86% overall figure, which is inflated by easy Tanzanian potato photos. Never invent or relabel a result.
- **Meaning colours** on `/check`: green = sure / healthy / go, amber = act this week / retake, red = act today, blue = the app is asking, violet = a human expert is involved.
- **Hindi and English** on every screen, with room for wider Devanagari text.

## Evidence on Hand
- Results: `web/lib/results.ts` (generated from `crop_doctor/outputs/metrics`), Exp 1-11 metrics and figures in `crop_doctor/outputs/`.
- Sample leaf photos: `crop_doctor/app/samples/` with expected outcomes in `samples.json`. `expert.jpg` and `healthy_tomato.jpg` carry stock-photo watermarks and must not be shown on the landing page.
- Reference photos: `web/public/reference/` (PlantVillage lab tomato photos, Tanzania potato farm photos, CC-BY-4.0).
- None: testimonials, user counts, press, partner logos, real farm photography of our users. Do not fabricate them.

## Product Principles
1. Say "not sure" rather than guess; a confident wrong answer is the worst outcome.
2. Lead with the hard number, and name easy results as easy.
3. A person checks what the model can't.
4. Work for a farmer on a cheap phone in daylight first.

## Accessibility & Inclusion
- Large touch targets, readable in sunlight, fast on slow data.
- Hindi (Devanagari) and English throughout.
- Respect reduced-motion settings.
