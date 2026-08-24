/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-chart-tabs> Lit component

   Tabbed container that switches between its pre-rendered chart
   children (e.g. Glide Path / Monte Carlo / Allocation). Mirrors the
   "chart_tabs" type in geap-agent/app/a2ui/catalog.py.

   General-purpose across tools: any A2UI surface (retirement, Monte
   Carlo, or a future tool) that needs a tabbed set of visualizations
   can reuse this one component instead of each tool hand-rolling its
   own tab-switching HTML/JS, which is what chat.js's
   getRetirementWidgetHtml()/switchRetirementChartTab() used to do
   with global onclick handlers and outerHTML swaps.

   Styles live in public/css/a2ui.css (.a2ui-chart-tabs, etc.).
   Props:
     tabs   {Array}  - required. [{ id, label }], in the same order
                        as `items`/children.
     active {String} - optional initial active tab id (defaults to
                        the first tab).
     items  {Array}  - pre-rendered child templates, one per tab, in
                        the same order as `tabs`. See a2ui-stat-grid.js
                        for why children are passed as a property
                        rather than light DOM content distributed via
                        `<slot>`.
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html, nothing } from 'lit';

export class A2uiChartTabs extends LitElement {
  static properties = {
    tabs:   { attribute: false },
    active: { type: String },
    items:  { attribute: false }
  };

  createRenderRoot() { return this; }

  constructor() {
    super();
    this._activeOverride = null;
  }

  get _activeTabId() {
    const tabs = Array.isArray(this.tabs) ? this.tabs : [];
    if (this._activeOverride && tabs.some((t) => t.id === this._activeOverride)) {
      return this._activeOverride;
    }
    if (this.active && tabs.some((t) => t.id === this.active)) return this.active;
    return tabs[0]?.id || null;
  }

  _selectTab(id) {
    this._activeOverride = id;
    this.requestUpdate();
  }

  render() {
    const tabs = Array.isArray(this.tabs) ? this.tabs : [];
    const items = Array.isArray(this.items) ? this.items : [];
    if (tabs.length === 0) return nothing;

    const activeId = this._activeTabId;
    const activeIndex = tabs.findIndex((t) => t.id === activeId);

    return html`
      <div class="a2ui-chart-tabs">
        <div class="a2ui-chart-tabs-nav" role="tablist">
          ${tabs.map((tab) => html`
            <button
              type="button"
              role="tab"
              class="a2ui-chart-tab-btn ${tab.id === activeId ? 'is-active' : ''}"
              aria-selected="${tab.id === activeId}"
              @click=${() => this._selectTab(tab.id)}
            >${tab.label}</button>
          `)}
        </div>
        <div class="a2ui-chart-tabs-panel">
          ${activeIndex >= 0 ? items[activeIndex] : nothing}
        </div>
        <div class="a2ui-chart-tabs-dials">
          ${tabs.map((tab) => html`
            <button
              type="button"
              class="a2ui-chart-dial-btn ${tab.id === activeId ? 'is-active' : ''}"
              @click=${() => this._selectTab(tab.id)}
            >✦ ${tab.label}</button>
          `)}
        </div>
      </div>
    `;
  }
}

if (!customElements.get('a2ui-chart-tabs')) {
  customElements.define('a2ui-chart-tabs', A2uiChartTabs);
}
