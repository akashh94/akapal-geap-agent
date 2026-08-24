/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-tool-card> Lit component

   Icon + title + body card. Mirrors the "tool_card" type in
   geap-agent/app/a2ui/catalog.py.

   Styles live in public/css/a2ui.css (.a2ui-tool-card, etc.).
   Props:
     title {String} - card heading (required)
     body  {String} - card body text (required)
     icon  {String} - optional emoji/text icon prefix
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html } from 'lit';

export class A2uiToolCard extends LitElement {
  static properties = {
    title: { type: String },
    body:  { type: String },
    icon:  { type: String }
  };

  createRenderRoot() { return this; }

  render() {
    return html`
      <div class="geap-stat-card a2ui-tool-card">
        <strong class="a2ui-tool-title">
          ${this.icon ? html`${this.icon} ` : ''}${this.title}
        </strong>
        <p class="a2ui-tool-body">${this.body}</p>
      </div>
    `;
  }
}

if (!customElements.get('a2ui-tool-card')) {
  customElements.define('a2ui-tool-card', A2uiToolCard);
}
