import type { Metadata } from "next";

import { ClubComingSoon } from "@/components/club/coming-soon";

export const metadata: Metadata = {
  robots: { index: false },
};

/** Club — "Prossimamente / Under Construction" (Step 3, no backend yet). */
export default function ClubPage() {
  return <ClubComingSoon />;
}
