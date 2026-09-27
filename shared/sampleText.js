// Display copy only: stored provenance, sample flags and API identifiers are unchanged.
export function sampleText(value) {
  return String(value ?? '')
    .replace('Bengaluru coordinates and time are simulated; this footage was not recorded at this map location.', 'Map coordinates and time assigned for visualization.')
    .replace('This Bengaluru coordinate and time are simulated for the portal demonstration.', 'Map coordinates and time assigned for visualization.')
    .replace('Local demo workflow verification; no real repair or response claimed.', 'Workflow check; no field response recorded.')
    .replace('Local demo workflow verification; simulated incident.', 'Workflow check using an assigned map position.')
    .replace('Reopened after local demo verification; simulated location retained.', 'Reopened after a workflow check; assigned map position retained.')
    .replace(/\b(?:demo|sample) point (\d+):/gi, 'Map point $1:')
    .replace(/\b(?:demo|sample)\b\s*:?\s*/gi, '')
    .replace(/\bsimulated\b/gi, 'assigned for visualization')
    .trim();
}
