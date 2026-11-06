"use client";

// Interface language. One setting drives both the screen text and the AI reply language.
// Screen text is translated for Hindi; other languages keep an English interface (replies still come in that
// language). Server text (questions, disease names, urgency...) is a fixed set of sentences, translated here.
import { useSyncExternalStore } from "react";

const KEY = "cd_language";
const listeners = new Set<() => void>();
const subscribe = (fn: () => void) => {
  listeners.add(fn);
  const onStorage = (e: StorageEvent) => e.key === KEY && fn();
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(fn);
    window.removeEventListener("storage", onStorage);
  };
};
const read = () => {
  try {
    return localStorage.getItem(KEY) ?? "English";
  } catch {
    return "English";
  }
};

export function setLanguage(l: string) {
  try {
    localStorage.setItem(KEY, l);
  } catch {}
  document.documentElement.lang = l === "Hindi" ? "hi" : "en";
  listeners.forEach((fn) => fn());
}

export function useLanguage(): string {
  return useSyncExternalStore(subscribe, read, () => "English");
}

const EN = {
  // header / footer
  check: "Check",
  checkLeaf: "Check a leaf",
  expert: "Expert",
  footerNote: "Crop Doctor is a student project. Always confirm with a local agriculture officer or KVK before spraying.",
  footerSources: "Treatment notes from TNAU, UC IPM and university extension services.",
  // home
  heroTag: "Tomato & potato leaf diseases",
  heroTitle: "A crop doctor that knows when it doesn't know.",
  heroText: "Send a photo of a sick leaf. When the app is sure, it tells you the disease, how urgent it is and what to do. When it isn't, it asks one question or sends your photo to an expert, instead of guessing.",
  checkNow: "Check a leaf now",
  trySample: "Try a sample photo",
  free: "Free",
  noInstall: "No app to install",
  languages8: "8 Indian languages",
  howItWorks: "How it works",
  step: "Step",
  flow1t: "Take a photo",
  flow1: "One sick leaf, in daylight. Blurry or dark photos are caught and you're asked to retake.",
  flow2t: "The app checks",
  flow2: "It compares the leaf with thousands of real field photos of tomato and potato diseases.",
  flow3t: "Get a clear answer",
  flow3: "What it is, how urgent, and what to do, in your language, with a Listen button.",
  kinds: "Three kinds of answer",
  kindsSub: "The app is honest about how sure it is. That's what makes it safe to trust.",
  sure: "Sure",
  sureT: "Names the disease, shows how urgent it is and what to do.",
  almost: "Almost sure",
  almostT: "Asks you one simple question about the leaf, then answers.",
  notSure: "Not sure",
  notSureT: "Sends your photo to an agriculture expert instead of guessing.",
  tryOwn: "Try it on your own plants",
  tryOwnT: "Works on any phone browser. The advice always ends with a reminder to check with your local agriculture officer before spraying.",
  // check: new photo
  loading: "Getting the crop doctor ready…",
  stepsSub: "3 steps · answer in a few seconds",
  whichCrop: "Which crop?",
  tomato: "Tomato",
  potato: "Potato",
  photoOf: "Photo of one sick leaf",
  goodPhoto: "Good photo",
  avoid: "Avoid",
  daylight: "Daylight",
  fillPhoto: "One leaf fills the photo",
  focus: "Spots in focus",
  blurry: "Blurry",
  tooDark: "Too dark",
  tooFar: "Too far away",
  photoReady: "Photo ready",
  differentPhoto: "Choose a different photo",
  takePhoto: "Take photo",
  gallery: "From gallery",
  cropFirst: "Choose the crop first",
  yourLanguage: "Your language",
  aiOff: "The AI assistant is off right now, so replies will be in English.",
  checkThis: "Check this leaf",
  noPlant: "No plant nearby? Try a sample photo",
  samplesNote: "Real field photos the model never saw during training, one for each kind of answer.",
  s1: "Checking photo quality",
  s2: "Looking at the leaf",
  s3: "Weighing the possible diseases",
  s4: "Writing your answer",
  // case screen
  checkNo: "Check",
  newPhoto: "New photo",
  leaf: "leaf",
  heroHealthy: "Healthy leaf",
  heroDisease: "Disease found",
  heroQuestion: "One quick question",
  heroExpert: "Sent to an expert",
  heroAnswered: "Checked by an expert",
  heroRetake: "New photo needed",
  goodNews: "Good news",
  mostLikely: "Most likely",
  veryLikely: "Very likely",
  likely: "Likely",
  possible: "Possible",
  lessLikely: "Less likely",
  actWithin: "Act within {t}",
  canWait: "Can wait",
  thisWeek: "This week",
  today: "Today",
  dmgLittle: "A little damage",
  dmgSome: "Some damage",
  dmgLot: "A lot of damage",
  dmgBad: "Badly damaged",
  dmgAbout: "About {p}% of the leaf looks damaged",
  dmgNote: "Rough estimate from the colours in the photo",
  causedBy: "Caused by",
  spreads: "How it spreads",
  recognise: "How to recognise it",
  cFungus: "Fungus",
  cWater: "Water mould (loves wet weather)",
  cBacteria: "Bacteria",
  cVirus: "Virus",
  cWhitefly: "Virus carried by whiteflies",
  spFast: "Spreads very fast",
  spMedium: "Spreads slowly to nearby leaves",
  spInsect: "Spread by insects",
  spContact: "Spread by hands and tools",
  whatToDo: "What to do now",
  aWeekly: "Check your plants every week",
  aWater: "Water at the base, keep leaves dry",
  aNewPhoto: "Send a new photo if spots appear",
  aPull: "Pull out sick plants, far from the field",
  aWhitefly: "Control whiteflies",
  aWash: "Wash hands and tools",
  aNoCure: "No spray cures a virus",
  aRemove: "Remove badly affected leaves",
  aTell: "Tell neighbouring farmers",
  aAsk: "Ask KVK / expert before spraying",
  notCertain: "Not 100% certain. Please confirm with a local expert before spraying.",
  doubleCheck: "An expert will also double-check this answer.",
  expertSays: "The expert says",
  couldBe: "It could be one of these",
  unknownPhoto: "This photo doesn't look like the diseases the assistant knows well.",
  waitingExpert: "Waiting for the expert",
  waitingNote: "Their answer will appear here. You can close this page and come back later.",
  waitSpray: "Wait for the expert before buying or spraying any chemical. Meanwhile, remove badly affected leaves and keep them away from the field.",
  lookClosely: "Look closely at your leaf",
  notSureExpert: "I'm not sure: ask an expert",
  extentWhy: "This tells us how quickly you need to act.",
  takeNew: "Take a new photo",
  chat: "Chat with the crop doctor",
  expertAnswer: "Expert answer",
  sources: "Sources",
  listen: "Listen",
  stop: "Stop",
  writing: "Writing your answer",
  askPlaceholder: "Ask anything, e.g. can I use an organic spray?",
  send: "Send",
  loadingCase: "Loading…",
  compareTitle: "Compare your leaf with these photos",
  typicalLook: "What it usually looks like",
  photoCredit: "Photo:",
  unfamiliar: "This photo looks unusual",
  unfamiliarT: "It doesn't look much like the photos the assistant learned from. An expert will check it to be safe.",
};
export type Key = keyof typeof EN;

const HI: Partial<Record<Key, string>> = {
  check: "जाँचें",
  checkLeaf: "पत्ता जाँचें",
  expert: "विशेषज्ञ",
  footerNote: "क्रॉप डॉक्टर एक छात्र प्रोजेक्ट है। दवा छिड़कने से पहले हमेशा अपने कृषि अधिकारी या KVK से पुष्टि करें।",
  footerSources: "उपचार की जानकारी TNAU, UC IPM और विश्वविद्यालय कृषि विस्तार सेवाओं से।",
  heroTag: "टमाटर और आलू के पत्तों के रोग",
  heroTitle: "एक फसल डॉक्टर जो जानता है कि वह कब नहीं जानता।",
  heroText: "बीमार पत्ते की फोटो भेजें। ऐप को यकीन हो तो वह रोग, कितनी जल्दी कदम उठाना है और क्या करना है, बताता है। यकीन न हो तो वह अंदाज़ा लगाने के बजाय एक सवाल पूछता है या आपकी फोटो विशेषज्ञ को भेजता है।",
  checkNow: "अभी पत्ता जाँचें",
  trySample: "नमूना फोटो से देखें",
  free: "मुफ़्त",
  noInstall: "कोई ऐप डाउनलोड नहीं",
  languages8: "8 भारतीय भाषाएँ",
  howItWorks: "यह कैसे काम करता है",
  step: "कदम",
  flow1t: "फोटो लें",
  flow1: "दिन की रोशनी में एक बीमार पत्ता। धुंधली या अंधेरी फोटो पकड़ी जाती है और दोबारा लेने को कहा जाता है।",
  flow2t: "ऐप जाँच करता है",
  flow2: "यह पत्ते की तुलना टमाटर और आलू के रोगों की हज़ारों असली खेत की फोटो से करता है।",
  flow3t: "साफ़ जवाब पाएँ",
  flow3: "रोग क्या है, कितना ज़रूरी है और क्या करें, आपकी भाषा में, सुनने के बटन के साथ।",
  kinds: "तीन तरह के जवाब",
  kindsSub: "ऐप ईमानदारी से बताता है कि उसे कितना यकीन है। इसी से उस पर भरोसा करना सुरक्षित है।",
  sure: "पक्का",
  sureT: "रोग का नाम, कितना ज़रूरी है और क्या करना है, बताता है।",
  almost: "लगभग पक्का",
  almostT: "पत्ते के बारे में एक आसान सवाल पूछता है, फिर जवाब देता है।",
  notSure: "पक्का नहीं",
  notSureT: "अंदाज़ा लगाने के बजाय आपकी फोटो कृषि विशेषज्ञ को भेजता है।",
  tryOwn: "अपने पौधों पर आज़माएँ",
  tryOwnT: "किसी भी फ़ोन के ब्राउज़र में चलता है। हर सलाह के अंत में याद दिलाया जाता है कि छिड़काव से पहले कृषि अधिकारी से पूछें।",
  loading: "फसल डॉक्टर तैयार हो रहा है…",
  stepsSub: "3 कदम · कुछ सेकंड में जवाब",
  whichCrop: "कौन सी फसल?",
  tomato: "टमाटर",
  potato: "आलू",
  photoOf: "एक बीमार पत्ते की फोटो",
  goodPhoto: "अच्छी फोटो",
  avoid: "ऐसी न लें",
  daylight: "दिन की रोशनी",
  fillPhoto: "पत्ता पूरी फोटो में हो",
  focus: "धब्बे साफ़ दिखें",
  blurry: "धुंधली",
  tooDark: "बहुत अंधेरी",
  tooFar: "बहुत दूर से",
  photoReady: "फोटो तैयार",
  differentPhoto: "दूसरी फोटो चुनें",
  takePhoto: "फोटो लें",
  gallery: "गैलरी से",
  cropFirst: "पहले फसल चुनें",
  yourLanguage: "आपकी भाषा",
  aiOff: "AI सहायक अभी बंद है, इसलिए जवाब अंग्रेज़ी में आएँगे।",
  checkThis: "यह पत्ता जाँचें",
  noPlant: "पास में पौधा नहीं? नमूना फोटो आज़माएँ",
  samplesNote: "असली खेत की फोटो जो मॉडल ने सीखते समय कभी नहीं देखीं, हर तरह के जवाब के लिए एक।",
  s1: "फोटो की गुणवत्ता जाँच रहे हैं",
  s2: "पत्ते को देख रहे हैं",
  s3: "संभावित रोगों को तौल रहे हैं",
  s4: "आपका जवाब लिख रहे हैं",
  checkNo: "जाँच",
  newPhoto: "नई फोटो",
  leaf: "पत्ता",
  heroHealthy: "स्वस्थ पत्ता",
  heroDisease: "रोग मिला",
  heroQuestion: "एक छोटा सवाल",
  heroExpert: "विशेषज्ञ को भेजा गया",
  heroAnswered: "विशेषज्ञ ने जाँचा",
  heroRetake: "नई फोटो चाहिए",
  goodNews: "अच्छी खबर",
  mostLikely: "सबसे संभावित",
  veryLikely: "बहुत संभावित",
  likely: "संभावित",
  possible: "हो सकता है",
  lessLikely: "कम संभावित",
  actWithin: "{t} के अंदर कदम उठाएँ",
  canWait: "रुक सकते हैं",
  thisWeek: "इस हफ़्ते",
  today: "आज ही",
  dmgLittle: "थोड़ा नुकसान",
  dmgSome: "कुछ नुकसान",
  dmgLot: "काफ़ी नुकसान",
  dmgBad: "बहुत ज़्यादा नुकसान",
  dmgAbout: "पत्ते का लगभग {p}% हिस्सा खराब दिखता है",
  dmgNote: "फोटो के रंगों से मोटा अनुमान",
  causedBy: "किससे होता है",
  spreads: "कैसे फैलता है",
  recognise: "कैसे पहचानें",
  cFungus: "फफूंद",
  cWater: "जल फफूंद (गीले मौसम में बढ़ती है)",
  cBacteria: "बैक्टीरिया",
  cVirus: "वायरस",
  cWhitefly: "सफ़ेद मक्खी से फैलने वाला वायरस",
  spFast: "बहुत तेज़ी से फैलता है",
  spMedium: "धीरे-धीरे पास के पत्तों में फैलता है",
  spInsect: "कीड़ों से फैलता है",
  spContact: "हाथों और औज़ारों से फैलता है",
  whatToDo: "अभी क्या करें",
  aWeekly: "हर हफ़्ते पौधे देखें",
  aWater: "जड़ में पानी दें, पत्ते सूखे रखें",
  aNewPhoto: "धब्बे दिखें तो नई फोटो भेजें",
  aPull: "बीमार पौधे उखाड़कर खेत से दूर करें",
  aWhitefly: "सफ़ेद मक्खी रोकें",
  aWash: "हाथ और औज़ार धोएँ",
  aNoCure: "वायरस का कोई स्प्रे इलाज नहीं",
  aRemove: "बुरी तरह खराब पत्ते हटाएँ",
  aTell: "पड़ोसी किसानों को बताएँ",
  aAsk: "छिड़काव से पहले KVK / विशेषज्ञ से पूछें",
  notCertain: "100% पक्का नहीं। छिड़काव से पहले स्थानीय विशेषज्ञ से पुष्टि करें।",
  doubleCheck: "एक विशेषज्ञ भी इस जवाब को दोबारा जाँचेगा।",
  expertSays: "विशेषज्ञ कहते हैं",
  couldBe: "इनमें से कोई एक हो सकता है",
  unknownPhoto: "यह फोटो उन रोगों जैसी नहीं दिखती जिन्हें सहायक अच्छी तरह जानता है।",
  waitingExpert: "विशेषज्ञ के जवाब का इंतज़ार",
  waitingNote: "उनका जवाब यहीं दिखेगा। आप यह पेज बंद करके बाद में आ सकते हैं।",
  waitSpray: "कोई भी दवा खरीदने या छिड़कने से पहले विशेषज्ञ का इंतज़ार करें। तब तक बुरी तरह खराब पत्ते हटाकर खेत से दूर रखें।",
  lookClosely: "अपने पत्ते को ध्यान से देखें",
  notSureExpert: "पता नहीं: विशेषज्ञ से पूछें",
  extentWhy: "इससे पता चलता है कि आपको कितनी जल्दी कदम उठाना है।",
  takeNew: "नई फोटो लें",
  chat: "फसल डॉक्टर से बात करें",
  expertAnswer: "विशेषज्ञ का जवाब",
  sources: "स्रोत",
  listen: "सुनें",
  stop: "रोकें",
  writing: "आपका जवाब लिख रहे हैं",
  askPlaceholder: "कुछ भी पूछें, जैसे क्या जैविक स्प्रे इस्तेमाल कर सकते हैं?",
  send: "भेजें",
  loadingCase: "लोड हो रहा है…",
  compareTitle: "अपने पत्ते की इन फोटो से तुलना करें",
  typicalLook: "यह आमतौर पर ऐसा दिखता है",
  photoCredit: "फोटो:",
  unfamiliar: "यह फोटो असामान्य लगती है",
  unfamiliarT: "यह उन फोटो जैसी नहीं दिखती जिनसे सहायक ने सीखा। सुरक्षा के लिए विशेषज्ञ इसे जाँचेगा।",
};

/* Fixed sentences that come from the server (diseases.json, decision.py, quality_gate.py). */
const SERVER_HI: Record<string, string> = {
  // disease names
  "Potato early blight": "आलू का अगेती झुलसा",
  "Healthy potato leaf": "स्वस्थ आलू का पत्ता",
  "Potato late blight": "आलू का पछेती झुलसा",
  "Tomato bacterial spot": "टमाटर का जीवाणु धब्बा रोग",
  "Tomato early blight": "टमाटर का अगेती झुलसा",
  "Healthy tomato leaf": "स्वस्थ टमाटर का पत्ता",
  "Tomato late blight": "टमाटर का पछेती झुलसा",
  "Tomato leaf mould": "टमाटर की पत्ती की फफूंद",
  "Tomato mosaic virus": "टमाटर मोज़ेक वायरस",
  "Tomato Septoria leaf spot": "टमाटर का सेप्टोरिया पत्ती धब्बा",
  "Tomato yellow leaf curl virus": "टमाटर पीला पत्ता मोड़ वायरस",
  "A different tomato problem": "टमाटर की कोई दूसरी समस्या",
  // key signs
  "brown spots with rings like a target, usually starting on older, lower leaves": "निशाने जैसे छल्लों वाले भूरे धब्बे, आमतौर पर पुराने, निचले पत्तों से शुरू",
  "even green colour, no spots or dark patches": "एक जैसा हरा रंग, कोई धब्बा या काला हिस्सा नहीं",
  "large dark, water-soaked patches; white fuzzy growth under the leaf in damp weather; can destroy a field within days": "बड़े काले, पानी से भीगे जैसे धब्बे; नमी में पत्ते के नीचे सफ़ेद रोएँदार परत; कुछ दिनों में पूरा खेत खराब कर सकता है",
  "many small, dark, greasy-looking spots, sometimes with a yellow edge; spreads with rain splash": "कई छोटे, काले, चिकने दिखने वाले धब्बे, कभी पीले किनारे के साथ; बारिश की छींटों से फैलता है",
  "brown spots with rings like a target, often with a yellow area around them, starting on lower leaves": "निशाने जैसे छल्लों वाले भूरे धब्बे, अक्सर चारों ओर पीला हिस्सा, निचले पत्तों से शुरू",
  "even green colour, no spots": "एक जैसा हरा रंग, कोई धब्बा नहीं",
  "large dark, water-soaked patches; white fuzzy growth under the leaf in damp weather; spreads very quickly": "बड़े काले, पानी से भीगे जैसे धब्बे; नमी में पत्ते के नीचे सफ़ेद रोएँदार परत; बहुत तेज़ी से फैलता है",
  "pale yellow patches on top of the leaf with olive-green or grey velvety mould underneath; common in humid greenhouses": "पत्ते के ऊपर हल्के पीले धब्बे और नीचे जैतूनी-हरी या स्लेटी मखमली फफूंद; नम ग्रीनहाउस में आम",
  "light and dark green mottled (patchwork) pattern, wrinkled or distorted leaves; spreads by hands, tools and seed": "हल्के और गहरे हरे रंग का चितकबरा पैटर्न, सिकुड़े या टेढ़े पत्ते; हाथों, औज़ारों और बीज से फैलता है",
  "many small round spots with dark borders and pale grey centres, often with tiny black dots inside": "काले किनारों और हल्के स्लेटी बीच वाले कई छोटे गोल धब्बे, अक्सर अंदर छोटे काले बिंदु",
  "leaves curl upwards, yellow leaf edges, small leaves and stunted plants; whiteflies often present": "पत्ते ऊपर की ओर मुड़ते हैं, किनारे पीले, छोटे पत्ते और बौने पौधे; अक्सर सफ़ेद मक्खियाँ दिखती हैं",
  "not one of the diseases the assistant was taught (for example pests or nutrient problems); an expert checks it": "उन रोगों में से नहीं जो सहायक ने सीखे (जैसे कीट या पोषक तत्वों की कमी); विशेषज्ञ इसे जाँचेगा",
  // follow-up questions
  "Look closely at the spots. Which looks more like your leaf?": "धब्बों को ध्यान से देखें। आपका पत्ता किसके जैसा दिखता है?",
  "Bigger brown spots with rings inside, like a target": "अंदर छल्लों वाले बड़े भूरे धब्बे, निशाने जैसे",
  "Many small round spots with dark edges and pale centres": "काले किनारों और हल्के बीच वाले कई छोटे गोल धब्बे",
  "Many tiny dark spots that look greasy or wet": "कई छोटे काले धब्बे जो चिकने या गीले दिखते हैं",
  "How do the damaged areas look?": "खराब हिस्से कैसे दिखते हैं?",
  "Dry brown spots with rings, mostly on older lower leaves": "छल्लों वाले सूखे भूरे धब्बे, ज़्यादातर पुराने निचले पत्तों पर",
  "Large dark patches that look wet, maybe white fuzz underneath, spreading fast": "बड़े काले गीले दिखने वाले धब्बे, नीचे शायद सफ़ेद रोएँ, तेज़ी से फैलते हुए",
  "Turn the leaf over. What do you see underneath?": "पत्ते को पलटें। नीचे क्या दिखता है?",
  "Olive-green or grey velvety mould under yellow patches": "पीले धब्बों के नीचे जैतूनी-हरी या स्लेटी मखमली फफूंद",
  "White fuzzy growth at the edge of dark wet-looking patches": "काले गीले धब्बों के किनारे सफ़ेद रोएँदार परत",
  "Nothing special underneath": "नीचे कुछ खास नहीं",
  "Which describes the leaves better?": "पत्तों के बारे में कौन सी बात ज़्यादा सही है?",
  "Light and dark green patchwork pattern, leaves wrinkled": "हल्के और गहरे हरे रंग का चितकबरा पैटर्न, पत्ते सिकुड़े हुए",
  "Leaves curling upwards with yellow edges, plant looks small": "पत्ते ऊपर मुड़ रहे हैं, किनारे पीले, पौधा छोटा दिखता है",
  "Leaves look normal and evenly green": "पत्ते सामान्य और एक जैसे हरे दिखते हैं",
  "Are there any spots or dead (brown) areas on the leaf?": "क्या पत्ते पर कोई धब्बा या सूखा (भूरा) हिस्सा है?",
  "No, the leaf is evenly green": "नहीं, पत्ता एक जैसा हरा है",
  "Yes, there are spots or brown areas": "हाँ, धब्बे या भूरे हिस्से हैं",
  // extent
  "How much of your crop is affected?": "आपकी फसल का कितना हिस्सा प्रभावित है?",
  "Just a few leaves": "बस कुछ पत्ते",
  "Many leaves on one or two plants": "एक-दो पौधों पर कई पत्ते",
  "Many plants": "कई पौधे",
  // urgency
  "24 hours": "24 घंटे",
  "2-3 days": "2-3 दिन",
  "2 days": "2 दिन",
  "3 days": "3 दिन",
  "this week": "इस हफ़्ते",
  "This disease can spread through a whole field within days.": "यह रोग कुछ ही दिनों में पूरे खेत में फैल सकता है।",
  "There is no cure for a virus. Remove infected plants and control the insects (whiteflies) that spread it.": "वायरस का कोई इलाज नहीं है। बीमार पौधे हटाएँ और इसे फैलाने वाले कीड़ों (सफ़ेद मक्खी) को रोकें।",
  "There is no cure for a virus. Remove infected plants; it spreads on hands and tools.": "वायरस का कोई इलाज नहीं है। बीमार पौधे हटाएँ; यह हाथों और औज़ारों से फैलता है।",
  "Already widespread; it will keep spreading.": "पहले से ही काफ़ी फैल चुका है; यह फैलता रहेगा।",
  "Treat before it spreads to more plants.": "और पौधों में फैलने से पहले इलाज करें।",
  "Caught early. Remove affected leaves and keep watching.": "जल्दी पकड़ में आया। खराब पत्ते हटाएँ और नज़र रखें।",
  // sample photo titles
  "Tomato leaf (clear case)": "टमाटर का पत्ता (साफ़ मामला)",
  "Potato leaf (clear case)": "आलू का पत्ता (साफ़ मामला)",
  "Leaf that needs one question": "पत्ता जिसके लिए एक सवाल चाहिए",
  "Unclear leaf (goes to an expert)": "अस्पष्ट पत्ता (विशेषज्ञ को जाता है)",
  "Blurry photo (asks to retake)": "धुंधली फोटो (दोबारा लेने को कहता है)",
  // photo quality
  "The photo is too small. Please send the original photo, not a thumbnail.": "फोटो बहुत छोटी है। कृपया असली फोटो भेजें, छोटी कॉपी नहीं।",
  "The photo is too dark. Please take it in daylight, without shade over the leaf.": "फोटो बहुत अंधेरी है। दिन की रोशनी में, पत्ते पर छाया के बिना लें।",
  "The photo is too bright. Avoid direct sun glare; shade the leaf with your hand.": "फोटो बहुत चमकीली है। सीधी धूप से बचें; हाथ से पत्ते पर छाया करें।",
  "The photo is blurry. Hold the phone steady, tap the leaf on screen to focus, then take it.": "फोटो धुंधली है। फ़ोन स्थिर रखें, स्क्रीन पर पत्ते को छूकर फ़ोकस करें, फिर फोटो लें।",
  "I can't find a leaf in this photo. Please photograph one affected leaf filling most of the frame.": "इस फोटो में पत्ता नहीं मिला। एक बीमार पत्ते की फोटो लें जो फ्रेम का ज़्यादातर हिस्सा भरे।",
};
const SERVER_KEYS = Object.keys(SERVER_HI).sort((a, b) => b.length - a.length);

export type T = ((k: Key, vars?: Record<string, string | number>) => string) & { server: (s?: string | null) => string; hi: boolean };

export function makeT(language: string): T {
  const hi = language === "Hindi";
  const t = ((k: Key, vars?: Record<string, string | number>) => {
    let s = (hi && HI[k]) || EN[k];
    if (vars) for (const [n, v] of Object.entries(vars)) s = s.replace(`{${n}}`, String(v));
    return s;
  }) as T;
  t.hi = hi;
  // Server sentences: exact match first, else replace each known sentence inside a longer message.
  t.server = (s) => {
    if (!s || !hi) return s ?? "";
    if (SERVER_HI[s]) return SERVER_HI[s];
    let out = s;
    for (const k of SERVER_KEYS) if (out.includes(k)) out = out.split(k).join(SERVER_HI[k]);
    return out;
  };
  return t;
}

export function useT(): T {
  return makeT(useLanguage());
}
