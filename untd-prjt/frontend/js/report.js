const Report = {
    _esc(str) {
        if (str === null || str === undefined) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    },

    _scoreColor(score) {
        if (score >= 80) return "#10b981";
        if (score >= 55) return "#f59e0b";
        return "#f43f5e";
    },

    _issueSeverity(severity) {
        const normalized = (severity || "info").toLowerCase();
        return ["error", "warning", "info", "style"].includes(normalized) ? normalized : "info";
    },

    _testRows(cases = []) {
        if (!cases.length) {
            return `
                <tr>
                    <td colspan="4">No test cases were produced for this run.</td>
                </tr>
            `;
        }

        const catColors = {
            unit: '#6366f1', integration: '#a855f7', bva: '#22d3ee',
            ecp: '#f59e0b', negative: '#f43f5e', regression: '#10b981',
            normal: '#6366f1', general: '#94a3b8'
        };

        return cases.map((test, index) => {
            const cat = (test.category || "General").toLowerCase();
            const catColor = catColors[cat] || '#94a3b8';
            return `
            <tr class="test-row" data-index="${index}" data-category="${this._esc(test.category || 'General')}">
                <td>${this._esc(test.name || "Unnamed test")}</td>
                <td><span class="cat-badge" style="color:${catColor};border-color:${catColor}33;background:${catColor}12">${this._esc(test.category || "General")}</span></td>
                <td>${test.passed ? '<span class="pass-badge">Pass</span>' : '<span class="fail-badge">Fail</span>'}</td>
                <td style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${this._esc(test.message || "-")}</td>
            </tr>
        `;}).join("");
    },

    renderOverview(data) {
        const score = Math.round(data.overall_score || 0);
        const scoreColor = this._scoreColor(score);
        const circumference = 339.292;
        const offset = circumference - (Math.max(0, Math.min(score, 100)) / 100) * circumference;
        const exec = data.execution;
        const staticAnalysis = data.static_analysis;
        const testing = data.testing;
        const security = data.security;
        const ai = data.ai_analysis;
        const performance = data.performance;
        const vulnerabilities = security?.vulnerabilities || [];
        const optimizations = ai?.optimizations || [];
        const issues = staticAnalysis?.issues || [];
        const passRate = testing?.total_tests ? Math.round((testing.passed / testing.total_tests) * 100) : 0;

        return `
            <div class="ai-summary-banner">
                <p>${this._esc(data.summary || "Analysis completed.")}</p>
            </div>

            <div class="report-card">
                <div class="report-card-header">
                    <div class="report-card-title">
                        <span class="material-symbols-outlined">analytics</span>
                        Overall Health
                    </div>
                </div>
                <div class="score-circle-wrapper">
                    <div class="score-circle">
                        <svg viewBox="0 0 120 120" aria-hidden="true">
                            <circle class="track" cx="60" cy="60" r="54"></circle>
                            <circle class="fill" cx="60" cy="60" r="54" style="stroke:${scoreColor};stroke-dashoffset:${offset};"></circle>
                        </svg>
                        <div class="score-value">
                            <div class="score-number">${score}</div>
                            <div class="score-label">Overall Score</div>
                        </div>
                    </div>
                    <div class="stat-grid" style="flex:1;min-width:min(100%,420px);margin-bottom:0;">
                        <div class="stat-card">
                            <div class="stat-label">Static Score</div>
                            <div class="stat-value">${staticAnalysis ? Math.round(staticAnalysis.score) : "N/A"}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Tests Passed</div>
                            <div class="stat-value">${testing ? `${testing.passed}/${testing.total_tests}` : "N/A"}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Security Risk</div>
                            <div class="stat-value">${this._esc(security?.risk_level || "unknown")}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Perf Grade</div>
                            <div class="stat-value">${this._esc(performance?.performance_grade || "N/A")}</div>
                        </div>
                    </div>
                </div>
            </div>

            ${exec ? `
                <div class="report-card">
                    <div class="report-card-header">
                        <div class="report-card-title">
                            <span class="material-symbols-outlined">${exec.success ? "check_circle" : "cancel"}</span>
                            Execution ${exec.success ? "Output" : "Failure"}
                        </div>
                        <div class="stat-label">${Math.round(exec.execution_time_ms || 0)} ms</div>
                    </div>
                    ${exec.stdout ? `<pre class="code-output">${this._esc(exec.stdout)}</pre>` : ""}
                    ${exec.stderr ? `<pre class="code-output error" style="margin-top:12px;">${this._esc(exec.stderr)}</pre>` : ""}
                </div>
            ` : ""}

            <div class="report-card">
                <div class="report-card-header">
                    <div class="report-card-title">
                        <span class="material-symbols-outlined">auto_awesome</span>
                        AI Assessment
                    </div>
                </div>
                <div class="ai-text-block" style="margin-bottom:14px;">
                    <h4><span class="material-symbols-outlined">psychology</span>Overall Assessment</h4>
                    <p>${this._esc(ai?.overall_assessment || ai?.logic_analysis || data.summary || "AI assessment is not available for this run.")}</p>
                </div>
                ${optimizations.length ? `
                    <div class="ai-list-grid">
                        ${optimizations.slice(0, 5).map((item, index) => `
                            <div class="ai-list-item">
                                <div class="ai-list-number num-optimize">${index + 1}</div>
                                <div class="ai-list-text">${this._esc(item)}</div>
                            </div>
                        `).join("")}
                    </div>
                ` : ""}
            </div>

            ${issues.length ? `
                <div class="report-card">
                    <div class="report-card-header">
                        <div class="report-card-title">
                            <span class="material-symbols-outlined">rule</span>
                            Static Analysis Issues
                        </div>
                        <div class="stat-label">${issues.length} findings</div>
                    </div>
                    <ul class="issue-list">
                        ${issues.slice(0, 10).map((issue) => {
                            const sev = this._issueSeverity(issue.severity);
                            return `
                                <li class="issue-item">
                                    <span class="issue-badge ${sev}">${sev}</span>
                                    <span>${this._esc(issue.message || "Issue detected")}</span>
                                    ${issue.line ? `<span class="issue-line">L${issue.line}</span>` : ""}
                                </li>
                            `;
                        }).join("")}
                    </ul>
                </div>
            ` : ""}

            <div class="report-card">
                <div class="report-card-header">
                    <div class="report-card-title">
                        <span class="material-symbols-outlined">science</span>
                        Testing Snapshot
                    </div>
                    <div class="stat-label">${testing?.total_tests || 0} total tests</div>
                </div>
                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-label">Pass Rate</div>
                        <div class="stat-value">${passRate}%</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Passed</div>
                        <div class="stat-value">${testing?.passed || 0}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Failed</div>
                        <div class="stat-value">${testing?.failed || 0}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Coverage Summary</div>
                        <div class="stat-value" style="font-size:0.82rem;line-height:1.6;">${this._esc(testing?.coverage_summary || "No coverage summary")}</div>
                    </div>
                </div>
            </div>

            ${vulnerabilities.length ? `
                <div class="report-card">
                    <div class="report-card-header">
                        <div class="report-card-title">
                            <span class="material-symbols-outlined">shield</span>
                            Security Findings
                        </div>
                    </div>
                    ${vulnerabilities.slice(0, 4).map((item) => `
                        <div class="insight-card critical">
                            <div class="insight-category">Security</div>
                            <div class="insight-title">${this._esc(item.title || item.name || "Potential vulnerability")}</div>
                            <div class="insight-desc">${this._esc(item.description || JSON.stringify(item))}</div>
                        </div>
                    `).join("")}
                </div>
            ` : ""}
        `;
    },

    renderPerformance(performance) {
        if (!performance) {
            return `
                <div class="empty-panel">
                    <span class="material-symbols-outlined">speed</span>
                    <p>No performance data available.</p>
                    <p style="color:var(--text-muted); font-size:0.8rem; margin-top:8px;">Run an analysis to generate execution time, memory usage, and complexity metrics.</p>
                </div>
            `;
        }

        const execMs = Math.round(performance.execution_time_ms || 0);
        const memory = Number(performance.memory_usage_mb || 0);
        const grade = performance.performance_grade || "N/A";
        const gradeClass = ["A", "B", "C", "D", "F"].includes(grade) ? `grade-${grade}` : "grade-C";

        return `
            <div class="report-card" style="grid-column:span 4;">
                <div class="report-card-header">
                    <div class="report-card-title">
                        <span class="material-symbols-outlined">query_stats</span>
                        Performance Grade
                    </div>
                </div>
                <div style="display:flex;align-items:center;justify-content:center;padding:12px 0 24px;">
                    <div class="grade-badge ${gradeClass}">${this._esc(grade)}</div>
                </div>
                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-label">Execution Time</div>
                        <div class="stat-value">${execMs} ms</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Memory Usage</div>
                        <div class="stat-value">${memory.toFixed(1)} MB</div>
                    </div>
                </div>
            </div>

            <div class="report-card" style="grid-column:span 8;">
                <div class="report-card-header">
                    <div class="report-card-title">
                        <span class="material-symbols-outlined">insights</span>
                        Complexity Signals
                    </div>
                </div>
                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-label">Time Complexity</div>
                        <div class="stat-value">${this._esc(performance.time_complexity_estimate || "N/A")}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Space Complexity</div>
                        <div class="stat-value">${this._esc(performance.space_complexity_estimate || "N/A")}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Peak Heap Estimate</div>
                        <div class="stat-value">${(memory * 1.2).toFixed(1)} MB</div>
                    </div>
                </div>
                <div class="ai-summary-banner" style="margin-bottom:0;">
                    <p>Execution finished in <strong>${execMs} ms</strong> using approximately <strong>${memory.toFixed(1)} MB</strong>. Complexity estimates are inferred from the analyzed source and runtime behavior.</p>
                </div>
            </div>
        `;
    },

    renderTesting(data) {
        const testing = data.testing;
        const whiteBox = data.white_box;
        const blackBox = data.black_box;
        const security = data.security;

        let html = "";

        if (whiteBox?.total_tests) {
            html += `
                <div class="report-card">
                    <div class="report-card-header">
                        <div class="report-card-title">
                            <span class="material-symbols-outlined">hub</span>
                            White-Box Testing
                        </div>
                        <div class="stat-label">${whiteBox.total_passed}/${whiteBox.total_tests}</div>
                    </div>
                    <div class="stat-grid">
                        <div class="stat-card"><div class="stat-label">Unit</div><div class="stat-value">${whiteBox.unit?.passed || 0}/${whiteBox.unit?.total_tests || 0}</div></div>
                        <div class="stat-card"><div class="stat-label">Integration</div><div class="stat-value">${whiteBox.integration?.passed || 0}/${whiteBox.integration?.total_tests || 0}</div></div>
                        <div class="stat-card"><div class="stat-label">Control Flow</div><div class="stat-value">${whiteBox.control_flow?.passed || 0}/${whiteBox.control_flow?.total_tests || 0}</div></div>
                        <div class="stat-card"><div class="stat-label">Data Flow</div><div class="stat-value">${whiteBox.data_flow?.passed || 0}/${whiteBox.data_flow?.total_tests || 0}</div></div>
                    </div>
                </div>
            `;
        }

        if (blackBox?.total_tests) {
            html += `
                <div class="report-card">
                    <div class="report-card-header">
                        <div class="report-card-title">
                            <span class="material-symbols-outlined">lan</span>
                            Black-Box Testing
                        </div>
                        <div class="stat-label">${blackBox.total_passed}/${blackBox.total_tests}</div>
                    </div>
                    <div class="stat-grid">
                        <div class="stat-card"><div class="stat-label">BVA</div><div class="stat-value">${blackBox.bva?.passed || 0}/${blackBox.bva?.total_tests || 0}</div></div>
                        <div class="stat-card"><div class="stat-label">ECP</div><div class="stat-value">${blackBox.ecp?.passed || 0}/${blackBox.ecp?.total_tests || 0}</div></div>
                        <div class="stat-card"><div class="stat-label">Decision Table</div><div class="stat-value">${blackBox.decision_table?.passed || 0}/${blackBox.decision_table?.total_tests || 0}</div></div>
                        <div class="stat-card"><div class="stat-label">State Transition</div><div class="stat-value">${blackBox.state_transition?.passed || 0}/${blackBox.state_transition?.total_tests || 0}</div></div>
                    </div>
                </div>
            `;
        }

        if (security) {
            html += `
                <div class="report-card">
                    <div class="report-card-header">
                        <div class="report-card-title">
                            <span class="material-symbols-outlined">shield</span>
                            Security Scan
                        </div>
                        <div class="stat-label">${this._esc(security.risk_level || "unknown")}</div>
                    </div>
                    <div class="report-card-body">${this._esc(security.summary || "Security summary unavailable.")}</div>
                </div>
            `;
        }

        html += `
            <div class="report-card">
                <div class="report-card-header">
                    <div class="report-card-title">
                        <span class="material-symbols-outlined">checklist</span>
                        Test Cases
                    </div>
                    <div class="stat-label">${testing?.total_tests || 0} cases</div>
                </div>
                <div class="test-table-wrap">
                    <table class="test-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Category</th>
                                <th>Status</th>
                                <th>Message</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${this._testRows(testing?.test_cases || [])}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        return html;
    },

    renderTestDetails(test) {
        if (!test) return '<p style="color:var(--text-muted); font-style:italic;">Select a test case to view detailed input/output context.</p>';

        return `
            <div class="test-details-panel">
                <div class="test-detail-item">
                    <div class="test-detail-label">Test Case</div>
                    <div class="test-detail-value" style="color:var(--accent-cyan); font-weight:700;">${this._esc(test.name)}</div>
                </div>
                <div class="test-detail-item">
                    <div class="test-detail-label">Status</div>
                    <div class="test-detail-value ${test.passed ? "pass" : "fail"}" style="font-weight:800;">
                        ${test.passed ? "✓ PASSED" : "✗ FAILED"}
                    </div>
                </div>
                <div class="test-detail-item">
                    <div class="test-detail-label">Input Data</div>
                    <pre class="test-detail-value">${this._esc(test.input_data || "N/A")}</pre>
                </div>
                <div class="test-detail-item">
                    <div class="test-detail-label">Expected Output</div>
                    <pre class="test-detail-value">${this._esc(test.expected || "N/A")}</pre>
                </div>
                <div class="test-detail-item">
                    <div class="test-detail-label">Actual Output</div>
                    <pre class="test-detail-value ${test.passed ? "" : "fail"}">${this._esc(test.actual || "N/A")}</pre>
                </div>
                ${test.message ? `
                    <div class="test-detail-item">
                        <div class="test-detail-label">Message</div>
                        <div class="test-detail-value" style="color:var(--text-secondary); font-family:var(--font-sans);">${this._esc(test.message)}</div>
                    </div>
                ` : ""}
            </div>
        `;
    }
};
