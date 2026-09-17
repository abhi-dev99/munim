import { Inter } from "next/font/google";
import "./globals.css";
import "./design-system.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800", "900"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata = {
  title: "Munim.ai — GST Compliance Dashboard",
  description: "AI-powered GST compliance agent for India's MSME traders. Track ITC, monitor suppliers, and recover lost credits.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className={`antialiased ${inter.className}`}>
        {children}
      </body>
    </html>
  );
}
