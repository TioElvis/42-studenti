import type { Metadata, Viewport } from "next";

import "./globals.css";
import { ThemeProvider, themeInitScript } from "@/providers/theme-provider";
import { I18nProvider } from "@/providers/i18n-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { RealtimeProvider } from "@/providers/realtime";
import { AppFrame } from "@/components/app-frame";
import { SITE_URL } from "@/lib/site";

const TITLE = "42 Studenti — Il portale degli studenti di 42 Roma";
const DESCRIPTION =
  "Il portale degli studenti di 42 Roma: La Bacheca, Eventi e Club. Codice, peer learning e 'na birra dopo er push.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: TITLE,
  description: DESCRIPTION,
  applicationName: "42 Studenti",
  keywords: ["42 Studenti", "42 Roma", "studenti 42 Roma", "eventi 42 Roma", "peer learning"],
  openGraph: {
    type: "website",
    locale: "it_IT",
    siteName: "42 Studenti",
    title: TITLE,
    description: DESCRIPTION,
    images: [{ url: "/rome-pixel.png", width: 1983, height: 793, alt: "Veduta pixel-art di Roma" }],
  },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0b0d0e",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it" data-theme="classic" suppressHydrationWarning>
      <head>
        {/* Apply the stored theme before paint to avoid a flash. */}
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <ThemeProvider>
          <I18nProvider>
            <AuthProvider>
              <RealtimeProvider>
                <AppFrame>{children}</AppFrame>
              </RealtimeProvider>
            </AuthProvider>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
