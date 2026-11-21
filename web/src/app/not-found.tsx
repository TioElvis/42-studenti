import type { Metadata } from "next";

import { NotFoundContent } from "@/components/not-found-content";

export const metadata: Metadata = {
  title: "404 — Pagina nun trovata · 42 Studenti",
};

/** Themed 404. Renders inside the app frame (<main>) for logged-in students,
 * matching the retro-OS look of the rest of the portal. */
export default function NotFound() {
  return <NotFoundContent />;
}
