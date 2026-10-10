// Finance & Admin Dashboard JavaScript

let currentFinanceActionClaim = null;

document.addEventListener("DOMContentLoaded", () => {
    loadFinanceOverview();
});

async function loadFinanceOverview() {
    const statusFilter = document.getElementById("filterStatus")?.value || "ALL";
    const categoryFilter = document.getElementById("filterCategory")?.value || "ALL";
    const flaggedFilter = document.getElementById("filterFlagged")?.value || "ALL";

    const tbody = document.getElementById("financeClaimsTableBody");
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">Loading claims and analytics...</td></tr>';

    try {
        const queryParams = new URLSearchParams({
            status: statusFilter,
            category: categoryFilter,
            flagged: flaggedFilter
        });

        const res = await fetch(`/api/finance/overview?${queryParams.toString()}`);
        if (!res.ok) throw new Error("Failed to load overview");
        const data = await res.json();

        // Update Analytics KPI Cards & Category Spend
        renderAnalytics(data.analytics);

        // Render Claims Master Table
        renderClaimsTable(data.claims);

    } catch (err) {
        console.error("Error loading finance overview:", err);
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-error">Failed to load data. Please refresh.</td></tr>';
    }
}

function renderAnalytics(analytics) {
    if (!analytics) return;

    // KPI Cards
    const elSpend = document.getElementById("statCompanySpend");
    const elPending = document.getElementById("statPendingDisbursement");
    const elHighRisk = document.getElementById("statHighRiskClaims");
    const elFlagRate = document.getElementById("statFlagRate");

    if (elSpend) elSpend.textContent = `$${analytics.total_approved_spend.toFixed(2)}`;
    if (elPending) elPending.textContent = `${analytics.pending_disbursement_count} ($${analytics.pending_disbursement_amount.toFixed(2)})`;
    if (elHighRisk) elHighRisk.textContent = `${analytics.flagged_claims_count}`;
    if (elFlagRate) elFlagRate.textContent = `${analytics.flag_rate_percent}% of total`;

    // Category Spend Grid
    const categorySpendGrid = document.getElementById("categorySpendContainer");
    if (categorySpendGrid && analytics.category_spend) {
        categorySpendGrid.innerHTML = Object.entries(analytics.category_spend).map(([cat, spend]) => {
            const count = analytics.category_counts[cat] || 0;
            return `
                <div class="category-stat-tile">
                    <div class="tile-header">
                        <span class="category-pill">${cat}</span>
                        <span class="tile-count">${count} claim(s)</span>
                    </div>
                    <div class="tile-amount">$${spend.toFixed(2)}</div>
                    <div class="tile-sub">Approved Spend</div>
                </div>
            `;
        }).join("");
    }
}

function renderClaimsTable(claims) {
    const tbody = document.getElementById("financeClaimsTableBody");

    if (!claims || claims.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No claims match the selected filters.</td></tr>';
        return;
    }

    tbody.innerHTML = "";
    claims.forEach(c => {
        const tr = document.createElement("tr");

        let flagsHtml = '<span class="badge badge-success">✓ Clean</span>';
        if (c.flags && c.flags.length > 0) {
            const hasDup = c.flags.some(f => f.type === "POSSIBLE_DUPLICATE");
            flagsHtml = `<span class="badge ${hasDup ? 'badge-danger' : 'badge-warning'}">
                ⚠️ ${c.flags.length} Flag(s)
            </span>`;
        }

        // Action button for Finance sign-off if in PENDING_FINANCE
        let actionBtn = `<a href="/claims/${c.id}" class="btn btn-sm btn-outline">🔍 Timeline</a>`;
        if (c.status === "PENDING_FINANCE") {
            actionBtn = `
                <div style="display: flex; gap: 0.35rem;">
                    <button class="btn btn-sm btn-primary" onclick="openFinanceModal(${c.id})">💳 Sign Off</button>
                    <a href="/claims/${c.id}" class="btn btn-sm btn-outline">Detail</a>
                </div>
            `;
        }

        tr.innerHTML = `
            <td><strong>#${c.id}</strong></td>
            <td>
                <strong>${escapeHtml(c.employee_name)}</strong>
            </td>
            <td><span class="text-muted">${escapeHtml(c.employee_department)}</span></td>
            <td><span class="category-pill">${c.category}</span></td>
            <td><strong>$${c.amount.toFixed(2)}</strong></td>
            <td>${c.expense_date}</td>
            <td><span class="badge status-${c.status}">${formatStatus(c.status)}</span></td>
            <td>${flagsHtml}</td>
            <td>${actionBtn}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Modal for Finance Disbursement Approval / Rejection
async function openFinanceModal(claimId) {
    try {
        const res = await fetch(`/api/claims/${claimId}`);
        if (!res.ok) return;
        const c = await res.json();
        currentFinanceActionClaim = c;

        let modal = document.getElementById("financeModal");
        if (!modal) {
            modal = createFinanceModal();
        }

        document.getElementById("finModalClaimId").textContent = `#${c.id}`;
        document.getElementById("finModalEmployee").textContent = `${c.employee_name} (${c.employee_department})`;
        document.getElementById("finModalAmount").textContent = `$${c.amount.toFixed(2)}`;
        document.getElementById("finModalCategory").textContent = c.category;
        document.getElementById("finModalComment").value = "";

        // Flags
        const flagBox = document.getElementById("finModalFlags");
        if (c.flags && c.flags.length > 0) {
            flagBox.innerHTML = c.flags.map(f => `
                <div class="alert alert-warning mb-1" style="padding: 0.4rem 0.6rem; font-size: 0.82rem;">
                    <strong>${f.type}:</strong> ${f.message}
                </div>
            `).join("");
        } else {
            flagBox.innerHTML = '<span class="text-muted">No policy flags recorded.</span>';
        }

        modal.style.display = "flex";
    } catch (err) {
        console.error("Error opening finance modal:", err);
    }
}

function closeFinanceModal() {
    const modal = document.getElementById("financeModal");
    if (modal) modal.style.display = "none";
    currentFinanceActionClaim = null;
}

async function submitFinanceDecision(action) {
    if (!currentFinanceActionClaim) return;
    const comment = document.getElementById("finModalComment").value.trim();

    if (action === "REJECT" && !comment) {
        alert("Please provide a reason when rejecting a claim.");
        document.getElementById("finModalComment").focus();
        return;
    }

    try {
        const res = await fetch(`/api/finance/${currentFinanceActionClaim.id}/action`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, comment })
        });

        const data = await res.json();
        if (!res.ok) {
            alert(data.error || "Action failed.");
            return;
        }

        closeFinanceModal();
        loadFinanceOverview();
    } catch (err) {
        console.error("Action error:", err);
    }
}

function createFinanceModal() {
    const div = document.createElement("div");
    div.id = "financeModal";
    div.className = "modal-overlay";
    div.innerHTML = `
        <div class="modal-card">
            <div class="modal-header">
                <h3>Finance Disbursement Sign-Off <span id="finModalClaimId"></span></h3>
                <button class="modal-close" onclick="closeFinanceModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="detail-grid">
                    <div><strong>Employee:</strong> <span id="finModalEmployee"></span></div>
                    <div><strong>Amount:</strong> <span id="finModalAmount" class="text-primary font-bold"></span></div>
                    <div><strong>Category:</strong> <span id="finModalCategory"></span></div>
                </div>

                <div style="margin-top: 1rem;">
                    <strong>Flags / Audit Warnings:</strong>
                    <div id="finModalFlags" style="margin-top: 0.35rem;"></div>
                </div>

                <div style="margin-top: 1rem;">
                    <label for="finModalComment"><strong>Finance Notes / Payment Reference:</strong></label>
                    <textarea 
                        id="finModalComment" 
                        class="form-control" 
                        rows="2" 
                        placeholder="Add disbursement reference or rejection reason..."
                    ></textarea>
                </div>
            </div>
            <div class="modal-footer" style="gap: 0.75rem;">
                <button class="btn btn-outline" onclick="closeFinanceModal()">Cancel</button>
                <button class="btn btn-outline" style="border-color: #fca5a5; color: #dc2626;" onclick="submitFinanceDecision('REJECT')">
                    ❌ Reject
                </button>
                <button class="btn btn-primary" onclick="submitFinanceDecision('APPROVE')">
                    ✅ Approve Disbursement
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(div);
    return div;
}

function formatStatus(status) {
    return status.replace(/_/g, ' ');
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    }[tag] || tag));
}

