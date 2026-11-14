import { Fraunces, IBM_Plex_Mono, Tiro_Devanagari_Hindi } from "next/font/google";

// Display serif (light), its Devanagari partner for Hindi headings, and a mono for numbers and labels.
export const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"], weight: ["300", "400"], style: ["normal", "italic"], display: "swap" });
export const tiro = Tiro_Devanagari_Hindi({ variable: "--font-tiro", subsets: ["devanagari"], weight: "400", style: ["normal", "italic"], display: "swap", preload: false });
export const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400", "500", "600"], display: "swap", preload: false });
