/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-view> Lit entry point   (public/js/a2ui/a2ui-view.js)

   Client-side renderer for A2UI (Agent-to-UI) envelopes that GEAP
   agents return from their signal tools.  An envelope is a small
   set of messages — createSurface / updateComponents /
   updateDataModel / deleteSurface — describing a tree of components
   by *type name* (e.g. "stat_tile").

   Public API:

     • <a2ui-view data-payload="<base64>">   (attribute-driven)
     • <a2ui-view data-root="stats">         (subtree selector)
     • element.payload = envelope            (property setter)
     • A2uiView.encodePayload(obj)           (static helper)
     • A2uiView.decodePayload(str)           (static helper)

   Each catalog type is rendered by its own Lit element defined in
   ./components/.  Lit's html`` tagged template literal provides
   automatic XSS-safe interpolation for all text values.

   Pure utilities (reduceEnvelope, encodePayload, decodePayload,
   CATALOG_TYPES) also live in ./a2ui-utils.js (UMD) so Node.js
   tests can require() them without a DOM or Lit dependency.

   Full write-up: docs/A2UI.md.
   Catalog source of truth: geap-agent/app/a2ui/catalog.py.
   ═══════════════════════════════════════════════════════════════ */

import { LitElement, html, nothing } from 'lit';
import './components/a2ui-surface.js';
import './components/a2ui-hero-cta.js';
import './components/a2ui-stat-grid.js';
import './components/a2ui-stat-tile.js';
import './components/a2ui-tool-grid.js';
import './components/a2ui-tool-card.js';
import './components/a2ui-safeguard-panel.js';
import './components/a2ui-safeguard-row.js';
import './components/a2ui-chart-tabs.js';
import './components/a2ui-glide-path-chart.js';
import './components/a2ui-monte-carlo-chart.js';
import './components/a2ui-allocation-chart.js';

// ---------------------------------------------------------------------------
// Envelope reducer — pure function.  The same logic also lives in
// a2ui-utils.js (UMD) for use by Node.js tests without a DOM.
// ---------------------------------------------------------------------------

export function reduceEnvelope(envelope) {
  let rootId = null;
  let components = {};

  for (const message of envelope.messages || []) {
    if (message.type === 'createSurface') {
      rootId = message.root || 'root';
    } else if (message.type === 'updateComponents') {
      for (const component of message.components || []) {
        components[component.id] = component;
      }
    } else if (message.type === 'deleteSurface') {
      rootId = null;
      components = {};
    }
    // updateDataModel: data is baked into props server-side; nothing to bind.
  }

  return { rootId, components };
}

// ---------------------------------------------------------------------------
// Per-type template builders.
//
// Each function uses a normal html`` tagged template literal with a known,
// static element tag, so Lit's template-literal security model (including
// Trusted Types enforcement) is fully respected.
//
// These must stay in sync with COMPONENT_TYPES in catalog.py and with the
// custom element definitions in ./components/.
// ---------------------------------------------------------------------------

function renderSurface(props, children) {
  return html`
    <a2ui-surface .title=${props.title} .subtitle=${props.subtitle} .items=${children}></a2ui-surface>
  `;
}

function renderHeroCta(props) {
  return html`
    <a2ui-hero-cta
      .title=${props.title}
      .body=${props.body}
      .eyebrow=${props.eyebrow}
    ></a2ui-hero-cta>
  `;
}

function renderStatGrid(children) {
  return html`<a2ui-stat-grid .items=${children}></a2ui-stat-grid>`;
}

function renderStatTile(props) {
  return html`
    <a2ui-stat-tile
      .label=${props.label}
      .value=${props.value}
      .sublabel=${props.sublabel}
      .tone=${props.tone}
    ></a2ui-stat-tile>
  `;
}

function renderToolGrid(children) {
  return html`<a2ui-tool-grid .items=${children}></a2ui-tool-grid>`;
}

function renderToolCard(props) {
  return html`
    <a2ui-tool-card
      .title=${props.title}
      .body=${props.body}
      .icon=${props.icon}
    ></a2ui-tool-card>
  `;
}

function renderSafeguardPanel(props, children) {
  return html`
    <a2ui-safeguard-panel .title=${props.title} .footnote=${props.footnote} .items=${children}></a2ui-safeguard-panel>
  `;
}

function renderSafeguardRow(props) {
  return html`
    <a2ui-safeguard-row
      .label=${props.label}
      .detail=${props.detail}
      ?active=${!!props.active}
    ></a2ui-safeguard-row>
  `;
}

function renderChartTabs(props, children) {
  return html`
    <a2ui-chart-tabs .tabs=${props.tabs} .active=${props.active} .items=${children}></a2ui-chart-tabs>
  `;
}

function renderGlidePathChart(props) {
  return html`<a2ui-glide-path-chart .points=${props.points}></a2ui-glide-path-chart>`;
}

function renderMonteCarloChart(props) {
  return html`
    <a2ui-monte-carlo-chart
      .points=${props.points}
      .target=${props.target}
      .targetLabel=${props.targetLabel}
    ></a2ui-monte-carlo-chart>
  `;
}

function renderAllocationChart(props) {
  return html`
    <a2ui-allocation-chart .title=${props.title} .segments=${props.segments}></a2ui-allocation-chart>
  `;
}

const TYPE_RENDERERS = {
  surface: (props, children) => renderSurface(props, children),
  hero_cta: (props) => renderHeroCta(props),
  stat_grid: (_props, children) => renderStatGrid(children),
  stat_tile: (props) => renderStatTile(props),
  tool_grid: (_props, children) => renderToolGrid(children),
  tool_card: (props) => renderToolCard(props),
  safeguard_panel: (props, children) => renderSafeguardPanel(props, children),
  safeguard_row: (props) => renderSafeguardRow(props),
  chart_tabs: (props, children) => renderChartTabs(props, children),
  glide_path_chart: (props) => renderGlidePathChart(props),
  monte_carlo_chart: (props) => renderMonteCarloChart(props),
  allocation_chart: (props) => renderAllocationChart(props)
};

function bytesToBase64(bytes) {
  let binary = '';
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function base64ToBytes(encoded) {
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

// ---------------------------------------------------------------------------
// Recursive component-tree builder.
// ---------------------------------------------------------------------------

function renderComponent(id, components, depth) {
  if (depth > 16) return nothing; // guard against cyclic children graph
  const component = components[id];
  if (!component) return nothing;

  const props = component.props || {};
  const children = (component.children || []).map((cid) =>
    renderComponent(cid, components, depth + 1)
  );

  const renderType = TYPE_RENDERERS[component.type];
  if (!renderType) {
    console.warn(`[a2ui-view] unknown component type "${component.type}" (id "${id}") — rendering its children only`);
    return html`${children}`;
  }
  return renderType(props, children);
}

// ---------------------------------------------------------------------------
// <a2ui-view> — the public compositor element
// ---------------------------------------------------------------------------

class A2uiView extends LitElement {
  static properties = {
    // Reflects the data-payload attribute (base64-encoded JSON envelope).
    dataPayload: { type: String, attribute: 'data-payload' },
    // Reflects the data-root attribute (override which component id to render).
    dataRoot: { type: String, attribute: 'data-root' }
  };

  // Light DOM: keep rendered output in the normal document tree so existing
  // global CSS rules (a2ui.css, styles.css tokens) apply without Shadow DOM
  // piercing.
  createRenderRoot() { return this; }

  constructor() {
    super();
    this._payloadObj = null;
    this._staticPlaceholderNodes = null;
  }

  connectedCallback() {
    super.connectedCallback();
    // planning.js (and chat.js) seed this element with static, server-side
    // skeleton/loading markup as its initial light DOM children *before* this
    // class is defined/upgraded. Lit's light-DOM render (createRenderRoot →
    // this) does not clear pre-existing, non-Lit-tracked content on its first
    // commit -- it only appends -- so without capturing and removing these
    // placeholder nodes once real content is ready, the skeleton would remain
    // forever, duplicated alongside (and un-styled relative to) the real
    // rendered output. Capture them once here so firstUpdated() can remove
    // exactly those nodes without disturbing anything Lit itself renders.
    if (!this._staticPlaceholderNodes) {
      this._staticPlaceholderNodes = Array.from(this.childNodes);
    }
  }

  firstUpdated() {
    if (!this._staticPlaceholderNodes) return;
    for (const node of this._staticPlaceholderNodes) {
      if (node.parentNode === this) this.removeChild(node);
    }
    this._staticPlaceholderNodes = null;
  }

  // ---- Public property API used by chat.js and planning.js ----

  get payload() {
    return this._payloadObj || null;
  }

  set payload(envelope) {
    this._payloadObj = envelope;
    this.requestUpdate();
  }

  // ---- Lit lifecycle ----

  willUpdate(changed) {
    // When the data-payload attribute changes, decode it into _payloadObj.
    if (!changed.has('dataPayload')) return;
    if (!this.dataPayload) {
      this._payloadObj = null;
      return;
    }
    try {
      this._payloadObj = A2uiView.decodePayload(this.dataPayload);
    } catch (err) {
      console.error('[a2ui-view] failed to decode data-payload attribute:', err);
      this._payloadObj = null;
    }
  }

  render() {
    const envelope = this._payloadObj;
    if (!envelope || !Array.isArray(envelope.messages)) return nothing;

    const { rootId, components } = reduceEnvelope(envelope);
    // data-root lets one envelope feed several <a2ui-view> mounts, each
    // showing a different subtree (planning.js uses "stats", "tools",
    // "safeguards" from one shared dashboard fetch).
    const effectiveRootId = this.dataRoot || rootId;
    if (!effectiveRootId || !components[effectiveRootId]) {
      console.warn(`[a2ui-view] envelope has no renderable component for root "${effectiveRootId}"`);
      return nothing;
    }

    return renderComponent(effectiveRootId, components, 0);
  }

  // ---- Static helpers used by chat.js and planning.js ----

  // Base64-encodes a payload for safe transport as an HTML attribute value.
  // Uses TextEncoder for a correct, standards-compliant UTF-8 → Base64 path.
  // The same functions are also available as encodePayload / decodePayload
  // in a2ui-utils.js (UMD) for Node.js test environments.
  static encodePayload(payload) {
    const json = JSON.stringify(payload);
    if (typeof TextEncoder !== 'undefined') {
      return bytesToBase64(new TextEncoder().encode(json));
    }
    if (typeof Buffer !== 'undefined') {
      return Buffer.from(json, 'utf8').toString('base64');
    }
    throw new Error('[a2ui-view] missing TextEncoder support for payload encoding');
  }

  static decodePayload(encoded) {
    if (typeof TextDecoder !== 'undefined') {
      return JSON.parse(new TextDecoder().decode(base64ToBytes(encoded)));
    }
    if (typeof Buffer !== 'undefined') {
      return JSON.parse(Buffer.from(encoded, 'base64').toString('utf8'));
    }
    throw new Error('[a2ui-view] missing TextDecoder support for payload decoding');
  }
}

if (!customElements.get('a2ui-view')) {
  customElements.define('a2ui-view', A2uiView);
}

// Expose on window for callers (chat.js, planning.js) that reference
// window.A2uiView as a global.
window.A2uiView = A2uiView;

export { A2uiView };
