import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ACM ID Card Studio — ACM NIT Surat",
  description: "Professional ID badge design & print-production workspace for ACM NIT Surat events.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-[#232324] text-[#FAFAFA] min-h-screen selection:bg-white/20 selection:text-white">
        {children}
      </body>
    </html>
  );
}
