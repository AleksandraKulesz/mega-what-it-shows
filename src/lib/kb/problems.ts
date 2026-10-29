// Splits a merged ticket into the problems its reports really describe.
// causes.ts places a report by tenant; the desk's one-day notes are a problem of their own,
// not a footnote under `parser`.
import { causeOf, uniqueById, type Cause, type Report, type Tenant } from '#lib/kb/causes';

export type Problem = Cause | 'one-day' | 'unplaced';

export function problemOf(r: Report, t: Tenant | undefined, oneDay: readonly string[]): Problem {
  if (oneDay.includes(r.id)) return 'one-day';
  return causeOf(r, t) ?? 'unplaced';
}

export type ProblemRow = { problem: Problem; reports: number; tenants: number; firstSeen: string; lastSeen: string };

export function splitTicket(
  reports: Report[],
  ticket: number,
  tenantOf: (r: Report) => Tenant | undefined,
  oneDay: readonly string[],
): { merged: number; rows: ProblemRow[] } {
  const merged = uniqueById(reports).filter((r) => r.mergedInto === ticket);
  const by = new Map<Problem, Report[]>();
  for (const r of merged) {
    const p = problemOf(r, tenantOf(r), oneDay);
    by.set(p, [...(by.get(p) ?? []), r]);
  }
  const rows = [...by.entries()]
    .map(([problem, rs]) => {
      const days = rs.map((r) => r.receivedAt.slice(0, 10)).sort();
      return { problem, reports: rs.length, tenants: new Set(rs.map((r) => r.tenant)).size, firstSeen: days[0], lastSeen: days[days.length - 1] };
    })
    .sort((a, b) => b.reports - a.reports);
  return { merged: merged.length, rows };
}
