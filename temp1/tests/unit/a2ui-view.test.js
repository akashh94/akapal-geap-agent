const test = require('node:test');
const assert = require('node:assert');
const path = require('path');

// ── Shim environment ────────────────────────────────────────────────────────
// Provide just enough of the browser globals the utils module references
// (btoa/atob).  No DOM required — all helpers are pure.

if (typeof global.btoa === 'undefined') {
  global.btoa = (s) => Buffer.from(s, 'binary').toString('base64');
  global.atob = (s) => Buffer.from(s, 'base64').toString('binary');
}

// ── Load the pure utilities ──────────────────────────────────────────────────
// a2ui-utils.js is a UMD module — loading via require() works fine.
const utils = require(path.resolve(__dirname, '..', '..', 'public', 'js', 'a2ui', 'a2ui-utils.js'));
const { CATALOG_TYPES, reduceEnvelope, encodePayload, decodePayload } = utils;

// ── Test helpers ─────────────────────────────────────────────────────────────

function envelopeWith(components, root = 'root') {
  return {
    version: 'a2ui/0.9',
    catalogId: 'geap.planning.v1',
    messages: [
      { type: 'createSurface', surfaceId: 's', root },
      { type: 'updateComponents', surfaceId: 's', components },
      { type: 'updateDataModel', surfaceId: 's', data: {} }
    ]
  };
}

// ── Payload encode/decode helpers ─────────────────────────────────────────────

test('a2ui-view - encodePayload/decodePayload round-trip', () => {
  const envelope = envelopeWith([
    { id: 'root', type: 'surface', props: {}, children: ['tile'] },
    { id: 'tile', type: 'stat_tile', props: { label: 'Probability of Success', value: '84%' }, children: [] }
  ]);

  const encoded = encodePayload(envelope);
  assert.ok(typeof encoded === 'string', 'encodePayload should return a string');
  assert.deepStrictEqual(decodePayload(encoded), envelope, 'round-trip should restore the original envelope');
});

// ── reduceEnvelope unit tests ─────────────────────────────────────────────────

test('a2ui-view - reduceEnvelope extracts rootId and components', () => {
  const envelope = envelopeWith([
    { id: 'root', type: 'surface', props: { title: 'T' }, children: [] }
  ]);
  const { rootId, components } = reduceEnvelope(envelope);
  assert.strictEqual(rootId, 'root');
  assert.ok(components['root']);
  assert.strictEqual(components['root'].props.title, 'T');
});

test('a2ui-view - reduceEnvelope handles deleteSurface by resetting state', () => {
  const envelope = {
    version: 'a2ui/0.9',
    catalogId: 'geap.planning.v1',
    messages: [
      { type: 'createSurface', surfaceId: 's', root: 'root' },
      { type: 'updateComponents', surfaceId: 's', components: [
        { id: 'root', type: 'surface', props: {}, children: [] }
      ] },
      { type: 'deleteSurface', surfaceId: 's' }
    ]
  };
  const { rootId, components } = reduceEnvelope(envelope);
  assert.strictEqual(rootId, null);
  assert.deepStrictEqual(components, {});
});

test('a2ui-view - reduceEnvelope returns empty for missing messages', () => {
  assert.deepStrictEqual(reduceEnvelope({ messages: [] }), { rootId: null, components: {} });
  assert.deepStrictEqual(reduceEnvelope({}), { rootId: null, components: {} });
});

// ── chart_tabs / chart component tree ────────────────────────────────────────
// Verify a realistic Monte Carlo / glide path / allocation tab tree reduces
// correctly -- this is the shape planning_agent's render_retirement_dashboard
// tool is expected to emit for the interactive chart widget.

test('a2ui-view - reduceEnvelope handles a chart_tabs component tree', () => {
  const envelope = envelopeWith([
    {
      id: 'root', type: 'chart_tabs',
      props: {
        tabs: [
          { id: 'glidepath', label: 'Glide Path' },
          { id: 'montecarlo', label: 'Monte Carlo' },
          { id: 'allocation', label: 'Allocation' }
        ],
        active: 'montecarlo'
      },
      children: ['glidepath-chart', 'montecarlo-chart', 'allocation-chart']
    },
    {
      id: 'glidepath-chart', type: 'glide_path_chart',
      props: { points: [{ age: 35, equities: 90, bonds: 8, cash: 2 }] },
      children: []
    },
    {
      id: 'montecarlo-chart', type: 'monte_carlo_chart',
      props: { points: [{ year: 2026, p10: 100000, p50: 150000, p90: 200000 }], target: 1000000 },
      children: []
    },
    {
      id: 'allocation-chart', type: 'allocation_chart',
      props: { title: 'Retirement Allocation Mix', segments: [{ label: 'U.S. Equities', pct: 45, value: '$37,903.57' }] },
      children: []
    }
  ]);

  const { rootId, components } = reduceEnvelope(envelope);
  assert.strictEqual(rootId, 'root');
  assert.strictEqual(components['root'].type, 'chart_tabs');
  assert.strictEqual(components['root'].props.tabs.length, 3);
  assert.deepStrictEqual(components['root'].children, ['glidepath-chart', 'montecarlo-chart', 'allocation-chart']);
  assert.strictEqual(components['montecarlo-chart'].props.target, 1000000);
});

// ── Catalog type coverage ─────────────────────────────────────────────────────
// Verify that CATALOG_TYPES lists all 12 known types so drift is caught early.

test('a2ui-view - CATALOG_TYPES covers all 12 catalog types', () => {
  const EXPECTED = [
    'surface', 'hero_cta', 'stat_grid', 'stat_tile',
    'tool_grid', 'tool_card', 'safeguard_panel', 'safeguard_row',
    'chart_tabs', 'glide_path_chart', 'monte_carlo_chart', 'allocation_chart'
  ];
  assert.strictEqual(CATALOG_TYPES.length, EXPECTED.length, 'CATALOG_TYPES should have exactly 12 entries');
  for (const type of EXPECTED) {
    assert.ok(CATALOG_TYPES.includes(type), `CATALOG_TYPES should include "${type}"`);
  }
});

