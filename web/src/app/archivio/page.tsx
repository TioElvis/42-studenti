import type { Metadata } from "next";

import { ContentBrowser } from "@/components/content/content-browser";

export const metadata: Metadata = {
  robots: { index: false },
};

/** Archivio — campus materials served from assets/archive/. */
export default function ArchivioPage() {
  return (
    <ContentBrowser
      section="archive"
      labelKey="archivio.label"
      descKey="archivio.desc"
      bar="ARCHIVIO.DIR"
    />
  );
}
