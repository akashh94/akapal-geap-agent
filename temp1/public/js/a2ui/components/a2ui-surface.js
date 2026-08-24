/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-surface> Lit component

   Root wrapper rendered by <a2ui-view> for every A2UI envelope.
   Mirrors the "surface" type in geap-agent/app/a2ui/catalog.py.

   Styles live in public/css/a2ui.css (.a2ui-surface, etc.).
   Using light DOM (createRenderRoot → this) so the app's existing
   design tokens and global CSS rules remain in scope. Children are
   passed as an `items` property rather than light DOM content
   distributed via `<slot>`, since `<slot>` only redistributes content
   inside a Shadow DOM tree — a light DOM component must own and emit
   its children directly.
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html } from 'lit';

export class A2uiSurface extends LitElement {
  static properties = {
    title:    { type: String },
    subtitle: { type: String },
    items:    { attribute: false }
  };

  createRenderRoot() { return this; }

  render() {
    return html`
      <div class="a2ui-surface">
        ${this.title ? html`<h3 class="a2ui-surface-title">${this.title}</h3>` : ''}
        ${this.subtitle ? html`<p class="a2ui-surface-subtitle">${this.subtitle}</p>` : ''}
        ${this.items}
      </div>
    `;
  }
}

if (!customElements.get('a2ui-surface')) {
  customElements.define('a2ui-surface', A2uiSurface);
}
