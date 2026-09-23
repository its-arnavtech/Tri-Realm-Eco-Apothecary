import type { Metadata } from "next";
import { DM_Sans, DM_Serif_Display } from "next/font/google";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import "./globals.css";

const sans = DM_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const serif = DM_Serif_Display({ subsets: ["latin"], weight: "400", style: ["normal", "italic"], variable: "--font-serif", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL("https://www.brew67potions.us"),
  title: { default: "brew67potions | Ideas inspired by three realms", template: "%s | brew67potions" },
  description: "An apothecary of ideas inspired by Forest, Ocean, and Mountain. Explore the realms and early brew concepts.",
  icons: { icon: "/favicon.svg" },
  openGraph: { title: "brew67potions", description: "Ideas inspired by Forest, Ocean, and Mountain.", type: "website", images: [{ url: "/images/tri-realm-hero.webp", width: 1792, height: 1024, alt: "Concept apothecary vessels overlooking a coastal mountain landscape" }] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className={`${sans.variable} ${serif.variable}`}><body><a className="skip-link" href="#main">Skip to content</a><SiteHeader />{children}<SiteFooter /></body></html>;
}
