import { useEffect, useState } from "react";
import { api, type Progress } from "../../lib/api";
import { label, LABELS } from "../../lib/labels";
import { useUiStore } from "../../lib/store";

export function ProgressScreen() {
  const showZh = useUiStore((s) => s.showZhLabels);
  const level = useUiStore((s) => s.level);
  const [data, setData] = useState<Progress | null>(null);

  useEffect(() => {
    api.progress().then(setData).catch(() => setData(null));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
      <h1 className="font-serif text-3xl text-ink">{label(LABELS.progress, showZh)}</h1>
      <p className="mt-2 max-w-xl text-muted">{label(LABELS.progressStub, showZh)}</p>
      <dl className="mt-8 grid max-w-md grid-cols-2 gap-4">
        <Stat label="XP today" value={String(data?.xp_today ?? 0)} />
        <Stat label="Daily goal" value={String(data?.daily_goal ?? 100)} />
        <Stat label="Streak" value={`${data?.streak ?? 0} days`} />
        <Stat label="Your level" value={String(level)} />
      </dl>
    </div>
  );
}

function Stat({ label: name, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-muted/30 px-4 py-3">
      <dt className="text-xs uppercase tracking-wide text-muted">{name}</dt>
      <dd className="mt-1 font-serif text-2xl tabular-nums text-ink">{value}</dd>
    </div>
  );
}
