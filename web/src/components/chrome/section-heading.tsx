/** Section header with a blinking terminal underscore, e.g. "La bacheca_". */
export function SectionHeading({ label, desc }: { label: string; desc?: string }) {
  return (
    <div className="mb-6">
      <h2 className="font-display text-2xl font-bold">
        {label}
        <span className="cursor-blink" aria-hidden>_</span>
      </h2>
      {desc ? <p className="mt-1 text-sm text-[var(--text-muted)]">{desc}</p> : null}
    </div>
  );
}
