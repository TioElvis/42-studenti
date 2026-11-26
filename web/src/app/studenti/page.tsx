import type { Metadata } from "next";

import { StudentSearch } from "@/components/students/student-search";

export const metadata: Metadata = {
  robots: { index: false },
};

/** Studenti — search other 42 Roma students and open their profile. */
export default function StudentiPage() {
  return <StudentSearch />;
}
