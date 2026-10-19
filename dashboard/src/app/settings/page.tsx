import { readSettings, SETTING_DEFAULTS } from "@/lib/settings";
import { listLibrary } from "@/lib/library";
import { systemStatus } from "@/lib/system";
import { SettingsView } from "@/components/settings-view";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const [values, docs, sys] = await Promise.all([readSettings(), listLibrary(), systemStatus()]);
  const roots = ["Sources", "Library"].map((folder) => ({ folder, docs: docs.filter((d) => d.id.startsWith(`${folder}/`)).length }));
  return <SettingsView values={values} defaults={SETTING_DEFAULTS} installed={sys.installed} vault={process.env.VAULT_PATH ?? ""} library={roots} />;
}
