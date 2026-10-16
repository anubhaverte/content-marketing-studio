import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Card Studio — ACM NIT Surat ID Card Generator",
  description: "End-to-end event ID badge generation engine with deterministic SVG rendering, OpenCV photo processing, and print-ready export.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-50 text-slate-900 min-h-screen">
        {children}
      </body>
    </html>
  );
}
