import type { Metadata, Viewport } from "next";

import "./globals.css";
import { ThemeProvider, themeInitScript } from "@/providers/theme-provider";
import { I18nProvider } from "@/providers/i18n-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { RealtimeProvider } from "@/providers/realtime";
import { AppFrame } from "@/components/app-frame";

export const metadata: Metadata = {
  title: "42 Studenti",
  description:
    "Il portale degli studenti di 42 Roma: La Bacheca, Eventi e Club. Codice, peer learning e 'na birra dopo er push.",
  applicationName: "42 Studenti",
  robots: { index: false, follow: false },
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
