/* ============================================================
   DataAisle — animations.js
   Handles:
   - KPI number counter animation
   - Run pipeline button loading state
   - Chart.js global defaults
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

    /* ── KPI counter animation ── */
    animateCounters();

    /* ── Pipeline run button ── */
    initRunButton();

});

/* ----------------------------------------------------------
   Counter — animates .kpi-value elements from 0 to their value
   ---------------------------------------------------------- */
function animateCounters() {
    const els = document.querySelectorAll('.kpi-value[data-count]');
    els.forEach(el => {
        const target = parseFloat(el.dataset.count);
        const isFloat = el.dataset.count.includes('.');
        const duration = 900;
        const startTime = performance.now();

        function update(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            const current = eased * target;

            if (isFloat) {
                el.textContent = current.toFixed(1) + '%';
            } else if (target >= 1000) {
                el.textContent = Math.round(current).toLocaleString();
            } else {
                el.textContent = Math.round(current);
            }

            if (progress < 1) requestAnimationFrame(update);
        }

        requestAnimationFrame(update);
    });
}

/* ----------------------------------------------------------
   Run pipeline button — shows spinner while navigating
   ---------------------------------------------------------- */
function initRunButton() {
    const btn = document.getElementById('runPipelineBtn');
    if (!btn) return;

    btn.addEventListener('click', function (e) {
        btn.classList.add('loading');
        btn.innerHTML = '<span class="spinner"></span> Running...';
        // Re-enable after 8s in case of error
        setTimeout(() => {
            btn.classList.remove('loading');
            btn.innerHTML = `
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-1px;margin-right:5px">
                    <polygon points="3,1 12,6.5 3,12" fill="currentColor" stroke="none"/>
                </svg>
                Run pipeline`;
        }, 8000);
    });
}

/* ----------------------------------------------------------
   Chart.js global defaults — called from each page that uses charts
   ---------------------------------------------------------- */
function applyChartDefaults() {
    if (typeof Chart === 'undefined') return;

    Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = '#94a3b8';

    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
    Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
    Chart.defaults.plugins.tooltip.bodyColor = '#cbd5e1';
    Chart.defaults.plugins.tooltip.borderColor = '#1e293b';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.displayColors = false;

    Chart.defaults.scale.grid.color = '#f1f5f9';
    Chart.defaults.scale.grid.drawBorder = false;
    Chart.defaults.scale.ticks.color = '#94a3b8';
    Chart.defaults.scale.border = { display: false };
}
