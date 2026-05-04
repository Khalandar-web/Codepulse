/**
 * Boneyard.js - Premium Skeleton UI Loader
 * Generates and manages animated skeleton screens.
 */

const Boneyard = {
    mount: function(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
        <div class="boneyard-wrapper">
            <div class="bone-header-area">
                <div class="bone-box bone-title bone-shimmer"></div>
                <div class="bone-box bone-subtitle bone-shimmer"></div>
            </div>
            
            <div class="bone-grid">
                <div class="bone-card">
                    <div class="bone-circle bone-shimmer"></div>
                    <div class="bone-box bone-short bone-shimmer"></div>
                </div>
                <div class="bone-card">
                    <div class="bone-circle bone-shimmer"></div>
                    <div class="bone-box bone-short bone-shimmer"></div>
                </div>
                <div class="bone-card">
                    <div class="bone-circle bone-shimmer"></div>
                    <div class="bone-box bone-short bone-shimmer"></div>
                </div>
            </div>
            
            <div class="bone-body-area">
                <div class="bone-box bone-long bone-shimmer" style="animation-delay: 0.1s"></div>
                <div class="bone-box bone-medium bone-shimmer" style="animation-delay: 0.2s"></div>
                <div class="bone-box bone-full bone-shimmer" style="animation-delay: 0.3s"></div>
                <div class="bone-box bone-medium bone-shimmer" style="animation-delay: 0.4s"></div>
                <div class="bone-box bone-short bone-shimmer" style="animation-delay: 0.5s"></div>
            </div>
        </div>
        `;
    },

    updateStage: function(msg) {
        const stageEl = document.getElementById('loading-stage');
        if (stageEl) {
            stageEl.textContent = msg;
            // Add a quick pulse effect on update
            stageEl.classList.remove('pulse-update');
            void stageEl.offsetWidth; // trigger reflow
            stageEl.classList.add('pulse-update');
        }
    }
};

// Export to window
window.Boneyard = Boneyard;
