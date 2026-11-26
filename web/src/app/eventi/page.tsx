import type { Metadata } from "next";

import { EventsGrid } from "@/components/eventi/events-grid";

export const metadata: Metadata = {
  robots: { index: false },
};

/** Eventi — official 42 Roma events fetched via the local 42api wrapper (Step 2). */
export default function EventiPage() {
  return <EventsGrid />;
}
