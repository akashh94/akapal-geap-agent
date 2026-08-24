/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-safeguard-row> Lit component

   Single safeguard with an active/inactive status dot. Mirrors
   the "safeguard_row" type in geap-agent/app/a2ui/catalog.py.

   Styles live in public/css/a2ui.css (.a2ui-safeguard-row, etc.).
   Props:
     label  {String}  - safeguard name (required)
     detail {String}  - secondary detail text (required)
     active {Boolean} - whether the safeguard is currently active
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html } from 'lit';

export class A2uiSafeguardRow extends LitElement {
  static properties = {
    label:  { type: String },
    detail: { type: String },
    active: { type: Boolean }
  };

  createRenderRoot() { return this; }

  render() {
    const activeClass = this.active ? 'is-active' : 'is-inactive';
    const dotClass = this.active ? 'geap-badge-dot--active' : '';
    return html`
      <div class="a2ui-safeguard-row">
        <div>
          <strong>${this.label}</strong>
          <span class="a2ui-safeguard-detail">${this.detail}</span>
        </div>
        <span class="a2ui-safeguard-status ${activeClass}">
          <span class="geap-badge-dot ${dotClass}"></span>
          ${this.active ? 'Active' : 'Inactive'}
        </span>
      </div>
    `;
  }
}

if (!customElements.get('a2ui-safeguard-row')) {
  customElements.define('a2ui-safeguard-row', A2uiSafeguardRow);
}
