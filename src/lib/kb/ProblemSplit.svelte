<script lang="ts">
  import reports from '#lib/data/reports-4471.json';
  import notes from '#lib/data/desk-notes.json';
  import { splitTicket, type Problem } from '#lib/kb/problems';
  import { tenantOf } from '#lib/kb/locales';
  import type { Report } from '#lib/kb/causes';

  let { ticket, issues = {} }: { ticket: number; issues?: Partial<Record<Problem, string>> } = $props();

  const WHAT: Record<Problem, string> = {
    parser: 'shared parser reads day-first dates month first',
    hint: 'booking-v3 form hints MM/DD/YYYY, reads day first',
    'one-day': 'date moves by one day (time zone / DST)',
    unplaced: 'no tenant on file',
  };

  const issueNo = (url?: string) => url?.split('/').pop() ?? '';

  const split = $derived(splitTicket(reports as Report[], ticket, tenantOf, notes.oneDayMove));
</script>

<p class="sum">
  <strong>{split.merged}</strong> reports merged into #{ticket} ·
  <strong>{split.rows.length}</strong> {split.rows.length === 1 ? 'problem' : 'problems'}
</p>

<table>
  <thead><tr><th>problem</th><th>what it is</th><th>reports</th><th>tenants</th><th>seen</th><th>ticket</th></tr></thead>
  <tbody>
    {#each split.rows as row (row.problem)}
      <tr>
        <td><code>{row.problem}</code></td>
        <td>{WHAT[row.problem]}</td>
        <td>{row.reports}</td>
        <td>{row.tenants}</td>
        <td>{row.firstSeen} → {row.lastSeen}</td>
        <td>{#if issues[row.problem]}<a href={issues[row.problem]}>#{issueNo(issues[row.problem])}</a>{:else}none yet{/if}</td>
      </tr>
    {/each}
  </tbody>
</table>

<style>
  .sum { font-size: 1.1rem; }
</style>
