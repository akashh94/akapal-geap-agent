/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-stat-tile> Lit component

   Single labeled metric card. Mirrors the "stat_tile" type in
   geap-agent/app/a2ui/catalog.py.

   Styles live in public/css/a2ui.css (.a2ui-stat-tile, etc.).
   Props:
     label    {String} - metric label (required)
     value    {String} - metric value (required)
     sublabel {String} - optional secondary label beneath value
     tone     {String} - optional CSS tone variant (e.g. "positive")
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html } from 'lit';

export class A2uiStatTile extends LitElement {
  static properties = {
    label:    { type: String },
    value:    { type: String },
    sublabel: { type: String },
    tone:     { type: String }
  };

  createRenderRoot() { return this; }

  render() {
    const toneClass = this.tone ? ` a2ui-stat-tile--${this.tone}` : '';
    return html`
      <div class="geap-stat-card a2ui-stat-tile${toneClass}">
        <span class="a2ui-stat-label">${this.label}</span>
        <strong class="a2ui-stat-value">
          ${this.value}
          ${this.sublabel
            ? html`<span class="a2ui-stat-sublabel">${this.sublabel}</span>`
            : ''}
        </strong>
      </div>
    `;
  }
}

if (!customElements.get('a2ui-stat-tile')) {
  customElements.define('a2ui-stat-tile', A2uiStatTile);
}
