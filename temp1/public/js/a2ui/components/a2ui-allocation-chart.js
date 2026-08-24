/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-allocation-chart> Lit component

   Segmented allocation bar + legend (e.g. "U.S. Equities 45%",
   "Fixed Income 25%", ...). Mirrors the "allocation_chart" type in
   geap-agent/app/a2ui/catalog.py.

   Data-driven replacement for the hand-authored SVG string that used
   to live in chat.js's getRetirementWidgetHtml() -- segment widths
   and legend rows are now computed from `segments` instead of a
   single hardcoded demo mix.

   Styles live in public/css/a2ui.css (.a2ui-chart, etc.).
   Props:
     title    {String} - optional heading above the bar.
     segments {Array}  - required. Each entry:
                          { label, pct, value, color } where pct is a
                          0-100 share of the bar and value is an
                          already-formatted display string (e.g.
                          "$37,903.57").
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html, svg, nothing } from 'lit';

const WIDTH = 320;
const BAR_HEIGHT = 24;
const BAR_LEFT = 30;
const BAR_WIDTH = 260;
const BAR_TOP = 45;
const LEGEND_TOP = 95;
const LEGEND_ROW_HEIGHT = 20;
const DEFAULT_COLORS = ['#4F8EF7', '#A78BFA', '#FBBF24', '#34D399', '#F472B6', '#38BDF8'];

export class A2uiAllocationChart extends LitElement {
  static properties = {
    title: { type: String },
    segments: { attribute: false }
  };

  createRenderRoot() { return this; }

  render() {
    const segments = Array.isArray(this.segments) ? this.segments : [];
    if (segments.length === 0) return nothing;

    const totalPct = segments.reduce((sum, s) => sum + (s.pct || 0), 0) || 100;
    let cursor = BAR_LEFT;
    const bars = segments.map((s, i) => {
      const width = (BAR_WIDTH * (s.pct || 0)) / totalPct;
      const x = cursor;
      cursor += width;
      return { ...s, x, width, color: s.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length] };
    });

    const height = LEGEND_TOP + segments.length * LEGEND_ROW_HEIGHT + 10;

    return html`
      <div class="a2ui-chart a2ui-allocation-chart">
        ${svg`
          <svg width="100%" height="${height}" viewBox="0 0 ${WIDTH} ${height}" class="a2ui-chart-svg">
            ${this.title ? svg`<text x="${BAR_LEFT}" y="30" class="a2ui-chart-title">${this.title}</text>` : nothing}

            <rect x="${BAR_LEFT}" y="${BAR_TOP}" width="${BAR_WIDTH}" height="${BAR_HEIGHT}" rx="6" class="a2ui-chart-bar-track" />
            ${bars.map((b) => svg`
              <rect x="${b.x}" y="${BAR_TOP}" width="${b.width}" height="${BAR_HEIGHT}" style="fill:${b.color}" />
            `)}

            ${bars.map((b, i) => svg`
              <circle cx="40" cy="${LEGEND_TOP + i * LEGEND_ROW_HEIGHT}" r="4" style="fill:${b.color}" />
              <text x="50" y="${LEGEND_TOP + i * LEGEND_ROW_HEIGHT + 3}" class="a2ui-chart-legend-row-label">
                ${b.label} (${b.pct}%)
              </text>
              ${b.value ? svg`
                <text x="280" y="${LEGEND_TOP + i * LEGEND_ROW_HEIGHT + 3}" class="a2ui-chart-legend-row-value">${b.value}</text>
              ` : nothing}
            `)}
          </svg>
        `}
      </div>
    `;
  }
}

if (!customElements.get('a2ui-allocation-chart')) {
  customElements.define('a2ui-allocation-chart', A2uiAllocationChart);
}
