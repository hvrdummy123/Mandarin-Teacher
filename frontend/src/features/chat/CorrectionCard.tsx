type Props = {
  original: string;
  better: string;
  reason: string;
};

export function CorrectionCard({ original, better, reason }: Props) {
  return (
    <aside
      className="mt-2 rounded border border-muted/30 bg-paper/80 px-3 py-2 text-sm"
      aria-label="Correction"
    >
      <p className="text-muted line-through">{original}</p>
      <p className="font-serif text-ink">{better}</p>
      <p className="mt-1 text-xs text-muted">{reason}</p>
    </aside>
  );
}
