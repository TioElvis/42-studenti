import type { Metadata } from "next";

import { ProfileView } from "@/components/profile/profile-view";

export const metadata: Metadata = {
  robots: { index: false },
};

/** A student's profile (own or another 42 Roma student). */
export default async function ProfilePage({
  params,
}: {
  params: Promise<{ login: string }>;
}) {
  const { login } = await params;
  return <ProfileView login={decodeURIComponent(login)} />;
}
