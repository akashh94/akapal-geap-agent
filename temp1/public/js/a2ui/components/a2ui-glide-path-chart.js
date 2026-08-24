/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-glide-path-chart> Lit component

   Stacked-area glide path chart (equities / bonds / cash mix over
   age). Mirrors the "glide_path_chart" type in
   geap-agent/app/a2ui/catalog.py.

   Data-driven replacement for the hand-authored SVG string that used
   to live in chat.js's getRetirementWidgetHtml() -- the shape of the
   picture is unchanged, but every coordinate is now computed from
   `points` instead of hardcoded, so any agent-provided glide path
   renders correctly instead of only the one demo shape.

   Styles live in public/css/a2ui.css (.a2ui-chart, etc.).
   Props:
     points {Array} - required. Each entry: { age, equities, bonds, cash }
                       where equities/bonds/cash are 0-100 percentages
                       that sum to (approximately) 100 for that age.
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html, svg, nothing } from 'lit';

const WIDTH = 320;
const HEIGHT = 180;
const PLOT_LEFT = 30;
const PLOT_RIGHT = 290;
const PLOT_TOP = 30;
const PLOT_BOTTOM = 150;

function xForIndex(index, count) {
  if (count <= 1) return PLOT_LEFT;
  return PLOT_LEFT + ((PLOT_RIGHT - PLOT_LEFT) * index) / (count - 1);
}

function yForPct(pct) {
  const clamped = Math.max(0, Math.min(100, pct || 0));
  return PLOT_BOTTOM - ((PLOT_BOTTOM - PLOT_TOP) * clamped) / 100;
}

function areaPath(topValues, bottomValues, xs) {
  const topPoints = xs.map((x, i) => `${x},${yForPct(topValues[i])}`);
  const bottomPoints = xs.map((x, i) => `${x},${yForPct(bottomValues[i])}`).reverse();
  return `M ${[...topPoints, ...bottomPoints].join(' L ')} Z`;
}

export class A2uiGlidePathChart extends LitElement {
  static properties = {
    points: { attribute: false }
  };

  createRenderRoot() { return this; }

  render() {
    const points = Array.isArray(this.points) ? this.points : [];
    if (points.length === 0) return nothing;

    const xs = points.map((_, i) => xForIndex(i, points.length));
    const cashTop = points.map((p) => (p.cash || 0));
    const bondsTop = points.map((p, i) => (p.cash || 0) + (p.bonds || 0));
    const equitiesTop = points.map(() => 100);
    const zero = points.map(() => 0);

    return html`
      <div class="a2ui-chart a2ui-glide-path-chart">
        ${svg`
          <svg width="100%" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" class="a2ui-chart-svg">
            <line x1="${PLOT_LEFT}" y1="30" x2="${PLOT_RIGHT}" y2="30" class="a2ui-chart-gridline" />
            <line x1="${PLOT_LEFT}" y1="60" x2="${PLOT_RIGHT}" y2="60" class="a2ui-chart-gridline" />
            <line x1="${PLOT_LEFT}" y1="90" x2="${PLOT_RIGHT}" y2="90" class="a2ui-chart-gridline" />
            <line x1="${PLOT_LEFT}" y1="120" x2="${PLOT_RIGHT}" y2="120" class="a2ui-chart-gridline a2ui-chart-gridline--dashed" />
            <line x1="${PLOT_LEFT}" y1="${PLOT_BOTTOM}" x2="${PLOT_RIGHT}" y2="${PLOT_BOTTOM}" class="a2ui-chart-axis" />
            <line x1="${PLOT_LEFT}" y1="30" x2="${PLOT_LEFT}" y2="${PLOT_BOTTOM}" class="a2ui-chart-axis" />

            <path d="${areaPath(cashTop, zero, xs)}" class="a2ui-chart-area a2ui-chart-area--cash" />
            <path d="${areaPath(bondsTop, cashTop, xs)}" class="a2ui-chart-area a2ui-chart-area--bonds" />
            <path d="${areaPath(equitiesTop, bondsTop, xs)}" class="a2ui-chart-area a2ui-chart-area--equities" />

            ${points.map((p, i) => svg`
              <text x="${xs[i]}" y="165" class="a2ui-chart-axis-label">Age ${p.age}</text>
            `)}
            <text x="${PLOT_LEFT - 5}" y="34" class="a2ui-chart-axis-label a2ui-chart-axis-label--end">100%</text>
            <text x="${PLOT_LEFT - 5}" y="94" class="a2ui-chart-axis-label a2ui-chart-axis-label--end">50%</text>
            <text x="${PLOT_LEFT - 5}" y="154" class="a2ui-chart-axis-label a2ui-chart-axis-label--end">0%</text>

            <text x="35" y="22" class="a2ui-chart-legend a2ui-chart-legend--equities">■ Equities</text>
            <text x="95" y="22" class="a2ui-chart-legend a2ui-chart-legend--bonds">■ Bonds</text>
            <text x="155" y="22" class="a2ui-chart-legend a2ui-chart-legend--cash">■ Cash</text>
          </svg>
        `}
      </div>
    `;
  }
}

if (!customElements.get('a2ui-glide-path-chart')) {
  customElements.define('a2ui-glide-path-chart', A2uiGlidePathChart);
}
