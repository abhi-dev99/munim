import "./globals.css";
import "./design-system.css";

export const metadata = {
  title: "Munim.ai — GST Compliance Dashboard",
  description: "AI-powered GST compliance agent for India's MSME traders. Track ITC, monitor suppliers, and recover lost credits.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
