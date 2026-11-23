import { ProfileView } from "@/components/profile/profile-view";

/** A student's profile (own or another 42 Roma student). */
export default async function ProfilePage({
  params,
}: {
  params: Promise<{ login: string }>;
}) {
  const { login } = await params;
  return <ProfileView login={decodeURIComponent(login)} />;
}
