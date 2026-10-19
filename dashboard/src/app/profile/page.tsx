import { listResearchNotes, readProfileRaw } from "@/lib/vault";
import { sessionEntries, standingPreferences, topicsOf } from "@/lib/profile";
import { ProfileView, type Lesson } from "@/components/profile-view";

export const dynamic = "force-dynamic";

export default async function ProfilePage() {
  const [raw, notes] = await Promise.all([readProfileRaw(), listResearchNotes()]);
  const entries = sessionEntries(raw);
  const lessons: Lesson[] = notes
    .filter((n) => n.feedbackNote)
    .map((n) => ({
      slug: n.slug,
      text: n.feedbackNote ?? "",
      from: `from “${n.title.slice(0, 60)}”, rated ${n.feedbackRating === "up" ? "helpful" : "not helpful"}`,
    }));
  return <ProfileView raw={raw} standing={standingPreferences(raw)} entries={entries} topics={topicsOf(entries)} lessons={lessons} />;
}
