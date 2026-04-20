import "./globals.css";

export const metadata = { title: "Quant Copilot", description: "Personal equity research" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
