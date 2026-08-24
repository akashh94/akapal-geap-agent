/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-tool-grid> Lit component

   Responsive grid wrapper for <a2ui-tool-card> children. Mirrors
   the "tool_grid" type in geap-agent/app/a2ui/catalog.py.

   Styles live in public/css/styles.css (.planning-tools-grid).
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html } from 'lit';

export class A2uiToolGrid extends LitElement {
  static properties = {
    // See a2ui-stat-grid.js for why children are passed as a property
    // instead of light DOM content distributed via `<slot>`.
    items: { attribute: false }
  };

  createRenderRoot() { return this; }

  render() {
    return html`
      <div class="planning-tools-grid a2ui-tool-grid">
        ${this.items}
      </div>
    `;
  }
}

if (!customElements.get('a2ui-tool-grid')) {
  customElements.define('a2ui-tool-grid', A2uiToolGrid);
}
