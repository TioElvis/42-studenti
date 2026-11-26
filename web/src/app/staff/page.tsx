import type { Metadata } from "next";

import { StaffContact } from "@/components/staff/staff-contact";

export const metadata: Metadata = {
  robots: { index: false },
};

/** Staff — write to the 42 Roma staff; opens a pre-filled email in your client. */
export default function StaffPage() {
  return <StaffContact />;
}
