/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-safeguard-panel> Lit component

   Card that lists <a2ui-safeguard-row> children. Mirrors the
   "safeguard_panel" type in geap-agent/app/a2ui/catalog.py.

   Styles live in public/css/a2ui.css (.a2ui-safeguard-panel, etc.).
   Props:
     title    {String} - panel heading (optional)
     footnote {String} - small-print note beneath the rows (optional)
     items    {Array}  - pre-rendered <a2ui-safeguard-row> templates, passed
                         as a property rather than light DOM content. `<slot>`
                         only redistributes content inside a Shadow DOM tree;
                         this component intentionally uses the light DOM (see
                         createRenderRoot below) so its own render() must own
                         and emit its children directly instead of relying on
                         a `<slot>`.
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html } from 'lit';

export class A2uiSafeguardPanel extends LitElement {
  static properties = {
    title:    { type: String },
    footnote: { type: String },
    items:    { attribute: false }
  };

  createRenderRoot() { return this; }

  render() {
    return html`
      <div class="geap-stat-card a2ui-safeguard-panel">
        ${this.title
          ? html`<h4 class="a2ui-safeguard-title">${this.title}</h4>`
          : ''}
        <div class="a2ui-safeguard-rows">
          ${this.items}
        </div>
        ${this.footnote
          ? html`<div class="a2ui-safeguard-footnote">${this.footnote}</div>`
          : ''}
      </div>
    `;
  }
}

if (!customElements.get('a2ui-safeguard-panel')) {
  customElements.define('a2ui-safeguard-panel', A2uiSafeguardPanel);
}
