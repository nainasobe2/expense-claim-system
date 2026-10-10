// Approver / Manager Dashboard JavaScript

let currentReviewClaim = null;

document.addEventListener("DOMContentLoaded", () => {
    loadApprovalQueue();
});

async function loadApprovalQueue() {
    const tbody = document.getElementById("approverTableBody");
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Loading pending claims...</td></tr>';

    try {
        const res = await fetch("/api/approvals/queue");
        if (!res.ok) throw new Error("Failed to load queue");
        const claims = await res.json();

        updateApproverStats(claims);

        if (!claims || claims.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">🎉 All caught up! No claims pending review in your queue.</td></tr>';
            return;
        }

        tbody.innerHTML = "";
        claims.forEach(c => {
            const tr = document.createElement("tr");

            // Build Flags / Warning Pills
            let flagsHtml = '<span class="badge badge-success">✓ Clean</span>';
            if (c.flags && c.flags.length > 0) {
                flagsHtml = c.flags.map(f => {
                    const isDup = f.type === "POSSIBLE_DUPLICATE";
                    const badgeClass = isDup ? "badge-danger" : "badge-warning";
                    return `<span class="badge ${badgeClass}" title="${escapeHtml(f.message)}">
                        ${isDup ? '🚨 Duplicate Match' : '⚠️ Policy Warning'}
                    </span>`;
                }).join(" ");
            }

            // High Value / Escalation notice
            let escalationBadge = "";
            if (c.requires_finance_escalation) {
                escalationBadge = `<span class="badge badge-info" title="Approving will route this to Finance for secondary sign-off">⚡ Routes to Finance</span>`;
            }

            tr.innerHTML = `
                <td>
                    <strong>#${c.id}</strong>
                    <div><a href="/claims/${c.id}" class="text-primary" style="font-size: 0.75rem;">View Timeline</a></div>
                </td>
                <td>
                    <strong>${escapeHtml(c.employee_name)}</strong>
                    <div class="text-muted" style="font-size: 0.75rem;">${escapeHtml(c.employee_department)}</div>
                </td>
                <td><span class="category-pill">${c.category}</span></td>
                <td><strong style="font-size: 0.95rem;">$${c.amount.toFixed(2)}</strong></td>
                <td>${c.expense_date}</td>
                <td>
                    <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                        <div>${flagsHtml}</div>
                        ${escalationBadge ? `<div>${escalationBadge}</div>` : ''}
                    </div>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="openReviewModal(${c.id})">
                        <span>⚖️ Review</span>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error loading approval queue:", err);
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-error">Failed to load claims. Please try again.</td></tr>';
    }
}

function updateApproverStats(claims) {
    let pendingCount = claims.length;
    let flaggedCount = 0;
    let totalQueueValue = 0;

    claims.forEach(c => {
        totalQueueValue += c.amount;
        if (c.flags && c.flags.length > 0) flaggedCount++;
    });

    const elPending = document.getElementById("statPendingReview");
    const elFlagged = document.getElementById("statFlaggedReview");
    const elQueueVal = document.getElementById("statQueueValue");

    if (elPending) elPending.textContent = pendingCount;
    if (elFlagged) elFlagged.textContent = flaggedCount;
    if (elQueueVal) elQueueVal.textContent = `$${totalQueueValue.toFixed(2)}`;
}

async function openReviewModal(claimId) {
    try {
        const res = await fetch(`/api/claims/${claimId}`);
        if (!res.ok) return;
        const c = await res.json();
        currentReviewClaim = c;

        let modal = document.getElementById("reviewModal");
        if (!modal) {
            modal = createReviewModal();
        }

        document.getElementById("reviewModalClaimId").textContent = `#${c.id}`;
        document.getElementById("reviewModalEmployee").textContent = `${c.employee_name} (${c.employee_department})`;
        document.getElementById("reviewModalAmount").textContent = `$${c.amount.toFixed(2)}`;
        document.getElementById("reviewModalCategory").textContent = c.category;
        document.getElementById("reviewModalDate").textContent = c.expense_date;
        document.getElementById("reviewModalDesc").textContent = c.description;
        document.getElementById("reviewComment").value = "";

        // Warnings & Flags
        const flagBox = document.getElementById("reviewModalFlags");
        if (c.flags && c.flags.length > 0) {
            flagBox.innerHTML = c.flags.map(f => {
                let matchInfo = "";
                if (f.matched_claim_id) {
                    matchInfo = ` (Matched Claim <a href="/claims/${f.matched_claim_id}" target="_blank">#${f.matched_claim_id}</a>)`;
                }
                return `
                    <div class="alert alert-warning mb-2" style="padding: 0.5rem 0.75rem;">
                        <strong>${f.type}:</strong> ${f.message} ${matchInfo}
                    </div>
                `;
            }).join("");
            flagBox.style.display = "block";
        } else {
            flagBox.innerHTML = '<div class="alert alert-success" style="padding: 0.5rem 0.75rem;">✓ No policy or duplicate flags detected. Clean claim.</div>';
            flagBox.style.display = "block";
        }

        // Receipt
        const receiptBox = document.getElementById("reviewModalReceipt");
        if (c.receipt_path) {
            receiptBox.innerHTML = `
                <a href="${c.receipt_path}" target="_blank" class="btn btn-sm btn-outline">
                    📎 View Attached Receipt
                </a>
            `;
        } else {
            receiptBox.innerHTML = '<span class="text-muted">No receipt attached</span>';
        }

        // Escalation notice
        const escalationNotice = document.getElementById("reviewEscalationNotice");
        const isHighVal = c.amount > 250;
        const hasFlags = c.flags && c.flags.length > 0;
        if (isHighVal || hasFlags) {
            escalationNotice.innerHTML = `
                <div class="alert alert-info" style="font-size: 0.82rem; margin-top: 0.75rem;">
                    ℹ️ <strong>Workflow Notice:</strong> Because this claim ${isHighVal ? 'is over $250.00' : ''} ${isHighVal && hasFlags ? 'and ' : ''}${hasFlags ? 'has flags' : ''}, approving will route it to <strong>Finance</strong> for disbursement sign-off.
                </div>
            `;
            escalationNotice.style.display = "block";
        } else {
            escalationNotice.innerHTML = `
                <div class="alert alert-success" style="font-size: 0.82rem; margin-top: 0.75rem;">
                    ✓ <strong>Direct Approval:</strong> Clean claim under threshold. Approving will immediately finalize this claim.
                </div>
            `;
            escalationNotice.style.display = "block";
        }

        modal.style.display = "flex";
    } catch (err) {
        console.error("Error opening review modal:", err);
    }
}

function closeReviewModal() {
    const modal = document.getElementById("reviewModal");
    if (modal) modal.style.display = "none";
    currentReviewClaim = null;
}

async function submitReviewDecision(action) {
    if (!currentReviewClaim) return;
    const comment = document.getElementById("reviewComment").value.trim();

    if (action === "REJECT" && !comment) {
        alert("Please provide a reason/comment when rejecting a claim.");
        document.getElementById("reviewComment").focus();
        return;
    }

    const btnApprove = document.getElementById("btnModalApprove");
    const btnReject = document.getElementById("btnModalReject");
    btnApprove.disabled = true;
    btnReject.disabled = true;

    try {
        const res = await fetch(`/api/approvals/${currentReviewClaim.id}/action`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, comment })
        });

        const data = await res.json();
        if (!res.ok) {
            alert(data.error || "Action failed.");
            return;
        }

        closeReviewModal();
        loadApprovalQueue();
    } catch (err) {
        console.error("Action error:", err);
        alert("Network error processing decision.");
    } finally {
        btnApprove.disabled = false;
        btnReject.disabled = false;
    }
}

function createReviewModal() {
    const div = document.createElement("div");
    div.id = "reviewModal";
    div.className = "modal-overlay";
    div.innerHTML = `
        <div class="modal-card">
            <div class="modal-header">
                <h3>Review Claim <span id="reviewModalClaimId"></span></h3>
                <button class="modal-close" onclick="closeReviewModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="detail-grid">
                    <div><strong>Employee:</strong> <span id="reviewModalEmployee"></span></div>
                    <div><strong>Amount:</strong> <span id="reviewModalAmount" class="text-primary font-bold"></span></div>
                    <div><strong>Category:</strong> <span id="reviewModalCategory"></span></div>
                    <div><strong>Expense Date:</strong> <span id="reviewModalDate"></span></div>
                </div>

                <div style="margin-top: 1rem;">
                    <strong>Business Purpose:</strong>
                    <p id="reviewModalDesc" class="detail-description"></p>
                </div>

                <div style="margin-top: 1rem;">
                    <strong>Policy & Duplicate Checks:</strong>
                    <div id="reviewModalFlags" style="margin-top: 0.35rem;"></div>
                </div>

                <div style="margin-top: 1rem;">
                    <strong>Receipt Attachment:</strong>
                    <div id="reviewModalReceipt" style="margin-top: 0.35rem;"></div>
                </div>

                <div id="reviewEscalationNotice"></div>

                <div style="margin-top: 1.25rem;">
                    <label for="reviewComment"><strong>Reviewer Comment / Reason:</strong></label>
                    <textarea 
                        id="reviewComment" 
                        class="form-control" 
                        rows="2" 
                        placeholder="Add notes for the employee or reason for decision (mandatory if rejecting)..."
                    ></textarea>
                </div>
            </div>
            <div class="modal-footer" style="gap: 0.75rem;">
                <button class="btn btn-outline" onclick="closeReviewModal()">Cancel</button>
                <button id="btnModalReject" class="btn btn-outline" style="border-color: #fca5a5; color: #dc2626;" onclick="submitReviewDecision('REJECT')">
                    ❌ Reject Claim
                </button>
                <button id="btnModalApprove" class="btn btn-primary" onclick="submitReviewDecision('APPROVE')">
                    ✅ Approve Claim
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(div);
    return div;
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

