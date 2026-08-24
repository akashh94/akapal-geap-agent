/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-hero-cta> Lit component

   Purple gradient hero card. Mirrors the "hero_cta" type in
   geap-agent/app/a2ui/catalog.py.

   Styles live in public/css/a2ui.css (.a2ui-hero, etc.).
   Props:
     title   {String} - card heading (required)
     body    {String} - card body text (required)
     eyebrow {String} - optional badge text above the title
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html } from 'lit';

export class A2uiHeroCta extends LitElement {
  static properties = {
    title:   { type: String },
    body:    { type: String },
    eyebrow: { type: String }
  };

  createRenderRoot() { return this; }

  render() {
    return html`
      <div class="a2ui-hero">
        <div class="a2ui-hero-bar"></div>
        <div class="a2ui-hero-head">
          <div>
            <h4 class="a2ui-hero-title">${this.title}</h4>
          </div>
          ${this.eyebrow
            ? html`<span class="geap-badge geap-badge--purple">${this.eyebrow}</span>`
            : ''}
        </div>
        <p class="a2ui-hero-body">${this.body}</p>
      </div>
    `;
  }
}

if (!customElements.get('a2ui-hero-cta')) {
  customElements.define('a2ui-hero-cta', A2uiHeroCta);
}
