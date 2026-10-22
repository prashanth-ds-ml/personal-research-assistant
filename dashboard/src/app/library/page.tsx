import { listLibrary } from "@/lib/library";
import { LibraryView } from "@/components/library-view";

// The library is read fresh from the index every time.
export const dynamic = "force-dynamic";

export default async function LibraryPage() {
  return <LibraryView docs={await listLibrary()} />;
}
