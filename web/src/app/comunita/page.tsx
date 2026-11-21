import { Feed } from "@/components/bacheca/feed";

/** Comunità — the "eventi non ufficiali": sondaggi (RSVP posts) from the Bacheca,
 * gathered in one place. Created from the Bacheca ("Messaggio" → tipo Sondaggio). */
export default function ComunitaPage() {
  return <Feed postType="sondaggio" />;
}
