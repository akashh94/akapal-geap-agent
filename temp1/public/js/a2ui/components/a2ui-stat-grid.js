/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-stat-grid> Lit component

   Responsive grid wrapper for <a2ui-stat-tile> children. Mirrors
   the "stat_grid" type in geap-agent/app/a2ui/catalog.py.

   Styles live in public/css/styles.css (.planning-stats-grid).
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html } from 'lit';

export class A2uiStatGrid extends LitElement {
  static properties = {
    // Pre-rendered child templates (a2ui-stat-tile elements), passed as a
    // property rather than light DOM content. `<slot>` only redistributes
    // content inside a Shadow DOM tree; this component intentionally uses
    // the light DOM (see createRenderRoot below) so its own render() must
    // own and emit its children directly instead of relying on a `<slot>`.
    items: { attribute: false }
  };

  createRenderRoot() { return this; }

  render() {
    return html`
      <div class="planning-stats-grid a2ui-stat-grid">
        ${this.items}
      </div>
    `;
  }
}

if (!customElements.get('a2ui-stat-grid')) {
  customElements.define('a2ui-stat-grid', A2uiStatGrid);
}
