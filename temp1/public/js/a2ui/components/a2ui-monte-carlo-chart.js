/* ═══════════════════════════════════════════════════════════════
   GEAP — <a2ui-monte-carlo-chart> Lit component

   Monte Carlo projection fan chart (p10 / p50 / p90 wealth paths vs.
   a target value). Mirrors the "monte_carlo_chart" type in
   geap-agent/app/a2ui/catalog.py.

   Data-driven replacement for the hand-authored SVG string that used
   to live in chat.js's getRetirementWidgetHtml() -- every curve is
   now computed from `points` (smoothed with a lightweight midpoint
   quadratic-bezier technique, no charting library required) instead
   of a single hardcoded demo shape.

   Styles live in public/css/a2ui.css (.a2ui-chart, etc.).
   Props:
     points {Array}  - required. Each entry: { year, p10, p50, p90 }
                        (dollar values).
     target {Number} - optional target wealth value shown as a dashed
                        reference line.
     targetLabel {String} - optional label for the target line
                              (defaults to a formatted `target`).
   ═══════════════════════════════════════════════════════════════ */
import { LitElement, html, svg, nothing } from 'lit';

const WIDTH = 320;
const HEIGHT = 180;
const PLOT_LEFT = 30;
const PLOT_RIGHT = 290;
const PLOT_TOP = 20;
const PLOT_BOTTOM = 150;

function formatDollars(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '';
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

// Smooths a polyline into a single-path string using quadratic Bezier
// segments through the midpoints between consecutive points -- a small,
// dependency-free technique that avoids sharp corners without needing a
// charting library.
function smoothPath(xs, ys) {
  if (xs.length === 0) return '';
  if (xs.length === 1) return `M ${xs[0]},${ys[0]}`;

  let d = `M ${xs[0]},${ys[0]}`;
  for (let i = 0; i < xs.length - 1; i += 1) {
    const midX = (xs[i] + xs[i + 1]) / 2;
    const midY = (ys[i] + ys[i + 1]) / 2;
    d += ` Q ${xs[i]},${ys[i]} ${midX},${midY}`;
  }
  d += ` L ${xs[xs.length - 1]},${ys[xs.length - 1]}`;
  return d;
}

// Same curve as smoothPath(), but without the leading "M x,y" -- for
// appending onto an already-open path whose current point already sits at
// (xs[0], ys[0]).
function smoothPathContinuation(xs, ys) {
  return smoothPath(xs, ys).replace(/^M [^ ]+ /, '');
}

export class A2uiMonteCarloChart extends LitElement {
  static properties = {
    points: { attribute: false },
    target: { type: Number },
    targetLabel: { type: String }
  };

  createRenderRoot() { return this; }

  render() {
    const points = Array.isArray(this.points) ? this.points : [];
    if (points.length === 0) return nothing;

    const allValues = points.flatMap((p) => [p.p10, p.p50, p.p90]).filter((v) => typeof v === 'number');
    const maxValue = Math.max(this.target || 0, ...allValues, 1);
    const minValue = Math.min(0, ...allValues);

    const xs = points.map((_, i) => (points.length <= 1
      ? PLOT_LEFT
      : PLOT_LEFT + ((PLOT_RIGHT - PLOT_LEFT) * i) / (points.length - 1)));
    const yFor = (value) => PLOT_BOTTOM - ((PLOT_BOTTOM - PLOT_TOP) * (value - minValue)) / (maxValue - minValue || 1);

    const p10Ys = points.map((p) => yFor(p.p10 || 0));
    const p50Ys = points.map((p) => yFor(p.p50 || 0));
    const p90Ys = points.map((p) => yFor(p.p90 || 0));

    const bandPath = `${smoothPath(xs, p90Ys)} L ${xs[xs.length - 1]},${p10Ys[xs.length - 1]} `
      + `${smoothPathContinuation([...xs].reverse(), [...p10Ys].reverse())} Z`;
    const targetY = this.target ? yFor(this.target) : null;

    return html`
      <div class="a2ui-chart a2ui-monte-carlo-chart">
        ${svg`
          <svg width="100%" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" class="a2ui-chart-svg">
            <line x1="${PLOT_LEFT}" y1="20" x2="${PLOT_RIGHT}" y2="20" class="a2ui-chart-gridline" />
            <line x1="${PLOT_LEFT}" y1="63" x2="${PLOT_RIGHT}" y2="63" class="a2ui-chart-gridline" />
            <line x1="${PLOT_LEFT}" y1="107" x2="${PLOT_RIGHT}" y2="107" class="a2ui-chart-gridline" />
            <line x1="${PLOT_LEFT}" y1="${PLOT_BOTTOM}" x2="${PLOT_RIGHT}" y2="${PLOT_BOTTOM}" class="a2ui-chart-axis" />
            <line x1="${PLOT_LEFT}" y1="20" x2="${PLOT_LEFT}" y2="${PLOT_BOTTOM}" class="a2ui-chart-axis" />

            <path d="${bandPath}" class="a2ui-chart-band" />

            ${targetY !== null ? svg`
              <line x1="${PLOT_LEFT}" y1="${targetY}" x2="${PLOT_RIGHT}" y2="${targetY}" class="a2ui-chart-target-line" />
              <text x="${PLOT_RIGHT - 5}" y="${targetY - 4}" class="a2ui-chart-axis-label a2ui-chart-axis-label--end">
                Target: ${this.targetLabel || formatDollars(this.target)}
              </text>
            ` : nothing}

            <path d="${smoothPath(xs, p90Ys)}" fill="none" class="a2ui-chart-line a2ui-chart-line--optimistic" />
            <path d="${smoothPath(xs, p50Ys)}" fill="none" class="a2ui-chart-line a2ui-chart-line--median" />
            <path d="${smoothPath(xs, p10Ys)}" fill="none" class="a2ui-chart-line a2ui-chart-line--conservative" />

            ${points.map((p, i) => svg`
              <text x="${xs[i]}" y="165" class="a2ui-chart-axis-label">${p.year}</text>
            `)}

            <text x="40" y="35" class="a2ui-chart-legend a2ui-chart-legend--optimistic">▲ 90% (Optimistic)</text>
            <text x="40" y="47" class="a2ui-chart-legend a2ui-chart-legend--median">■ 50% (Median)</text>
            <text x="40" y="59" class="a2ui-chart-legend a2ui-chart-legend--conservative">▼ 10% (Conservative)</text>
          </svg>
        `}
      </div>
    `;
  }
}

if (!customElements.get('a2ui-monte-carlo-chart')) {
  customElements.define('a2ui-monte-carlo-chart', A2uiMonteCarloChart);
}
