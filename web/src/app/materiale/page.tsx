import type { Metadata } from "next";

import { ContentBrowser } from "@/components/content/content-browser";

export const metadata: Metadata = {
  robots: { index: false },
};

/** Materiale didattico — student repo/project files served from assets/material/. */
export default function MaterialePage() {
  return (
    <ContentBrowser
      section="material"
      labelKey="materiale.label"
      descKey="materiale.desc"
      bar="MATERIALE.REPO"
    />
  );
}
