function renderPlanning() {
  setTimeout(mountPlanningDashboard, 0);

  return `
    <section class="page-band">
      <div class="shell">
        <div class="page-title-row">
          <h1>Planning & Retirement</h1>
          <button class="text-button" type="button" data-refresh>Refresh <span>${mockData.user.refreshedAt}</span></button>
        </div>
      </div>
    </section>

    <section class="shell" style="margin-top: 24px; margin-bottom: 40px;">
      <div class="content-grid" style="padding-top: 0; padding-bottom: 0;">

        <!-- Left Column: AI Advisor & Stats -->
        <div>
          <!-- AI Retirement Advisor Hero -->
          <div class="geap-card" style="margin-bottom: 24px; padding: 24px; background: #fff; border-radius: 8px; border: 1px solid #e2e8f0; position: relative; overflow: hidden;">
            <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #6B2D9B, #4F8EF7);"></div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
              <div>
                <h2 style="font-size: 18px; font-weight: 700; margin: 0; color: #1e293b;">✦ GEAP Intelligent Retirement Advisor</h2>
                <p style="font-size: 13px; color: #64748b; margin: 4px 0 0 0;">Active Wealth & Retirement Planning</p>
              </div>
              <span class="geap-badge" style="background: #fdf2f8; color: #db2777; border: 1px solid #fbcfe8; font-size: 11px; padding: 2px 8px; border-radius: 9999px;">AI Enabled</span>
            </div>
            <p style="font-size: 13px; line-height: 1.5; color: #334155; margin-bottom: 20px;">
              The Google Enterprise Agent Platform retirement optimizer simulates target date glide paths, runs Monte Carlo projection maps, and assesses your asset allocation to ensure a secure path to retirement. Click below to trigger a retirement health check directly with the assistant.
            </p>
            <button class="outline-button" onclick="if (typeof triggerChatQuery !== 'undefined') { triggerChatQuery('Run retirement planning health check.'); } return false;"
                    style="background: #6B2D9B; color: #fff; border-color: #6B2D9B; display: flex; align-items: center; gap: 6px;">
              <span>✦ Run Retirement Health Check</span>
            </button>
          </div>

          <!-- Retirement Projections Grid -- filled by planning_agent's A2UI dashboard, see mountPlanningDashboard() below -->
          <a2ui-view id="planning-stats-view" data-root="stats">${planningSkeletonGrid('planning-stats-grid', 4)}</a2ui-view>

          <!-- Tools Spotlight -->
          <a2ui-view id="planning-tools-view" data-root="tools">${planningSkeletonGrid('planning-tools-grid', 3)}</a2ui-view>
        </div>

        <!-- Right Column: Active Safeguards & Info -->
        <div>
          <a2ui-view id="planning-safeguards-view" data-root="safeguards">${planningSkeletonSafeguards()}</a2ui-view>
        </div>

      </div>
    </section>
  `;
}

function planningSkeletonGrid(gridClass, count) {
  const tiles = Array.from({ length: count })
    .map(() => `
      <div class="geap-card" style="padding: 16px; background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;">
        <span class="geap-skeleton-text" style="width: 90px; height: 10px; display: block;"></span>
        <span class="geap-skeleton-text" style="width: 60px; height: 20px; display: block; margin-top: 10px;"></span>
      </div>
    `)
    .join('');
  return `<div class="${gridClass}" style="margin-top: 24px; margin-bottom: 24px;">${tiles}</div>`;
}

function planningSkeletonSafeguards() {
  return `
    <div class="geap-card" style="padding: 20px; background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;">
      <span class="geap-skeleton-text" style="width: 140px; height: 12px; display: block; margin-bottom: 16px;"></span>
      <span class="geap-skeleton-text" style="width: 100%; height: 14px; display: block; margin-bottom: 10px;"></span>
      <span class="geap-skeleton-text" style="width: 100%; height: 14px; display: block; margin-bottom: 10px;"></span>
      <span class="geap-skeleton-text" style="width: 100%; height: 14px; display: block;"></span>
    </div>
  `;
}

// Fetches the same A2UI envelope the chat window renders for a retirement
// health check (routed through planning_agent) and feeds it into the three
// <a2ui-view> mounts above via `data-root`, so the page and the chat widget
// are backed by one implementation instead of two hardcoded copies of the
// same numbers. See docs/A2UI.md.
async function mountPlanningDashboard() {
  const statsEl = document.getElementById('planning-stats-view');
  const toolsEl = document.getElementById('planning-tools-view');
  const safeguardsEl = document.getElementById('planning-safeguards-view');
  if (!statsEl && !toolsEl && !safeguardsEl) return; // navigated away already

  try {
    const { a2ui } = await GeapApp.queryA2ui('Show my retirement planning dashboard.');
    const envelope = a2ui || (typeof mockData !== 'undefined' ? mockData.planningDashboard : null);
    if (!envelope) {
      console.warn('[planning] planning_agent did not return an A2UI dashboard payload');
      return;
    }
    if (!a2ui) {
      console.info('[planning] using mock planning dashboard (agent returned no A2UI payload)');
    }
    if (statsEl) statsEl.payload = envelope;
    if (toolsEl) toolsEl.payload = envelope;
    if (safeguardsEl) safeguardsEl.payload = envelope;
  } catch (err) {
    console.error('[planning] failed to load the retirement dashboard:', err);
  }
}
