import type { Metadata } from "next";

import { Hero } from "@/components/chrome/hero";
import { Feed } from "@/components/bacheca/feed";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

/** La Bacheca — the protected student feed (Step 1, core MVP). */
export default function BachecaPage() {
  return (
    <>
      <Hero />
      <Feed />
    </>
  );
}
