export function fmtPrice(n: number | null | undefined): string {
  if (n == null) return "—";
  return (
    "¥" +
    Number(n).toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })
  );
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${Number(n).toFixed(2)}%`;
}

export function pctClass(n: number | null | undefined): string {
  if (n == null) return "text-[var(--text-tertiary)]";
  return n > 0 ? "text-emerald-600" : n < 0 ? "text-rose-600" : "text-[var(--text-tertiary)]";
}

export function shortName(name: string | undefined): string {
  if (!name) return "—";
  return name.includes("·") ? name.split("·").slice(1).join("·").trim() : name;
}

export function safeHtml(s: unknown): string {
  return String(s ?? "").replace(/[<>&"]/g, (c) => ({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    '"': "&quot;",
  })[c] as string);
}
