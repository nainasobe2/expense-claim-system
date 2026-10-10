// Employee Portal JavaScript: Dynamic Policies, Inline Validation, Claim Submission, and Tracking

let activePolicies = {};

document.addEventListener("DOMContentLoaded", () => {
    loadPolicies();
    loadMyClaims();
    setupDateLimits();
});

// Setup date input with today as max allowable date (cannot be future date)
function setupDateLimits() {
    const dateInput = document.getElementById("expense_date");
    if (dateInput) {
        const today = new Date().toISOString().split("T")[0];
        dateInput.setAttribute("max", today);
        dateInput.value = today;
    }
}

// Load policies from API to populate dropdown and cache rules
async function loadPolicies() {
    try {
        const res = await fetch("/api/policies");
        if (!res.ok) return;
        const policies = await res.json();
        
        const select = document.getElementById("category");
        if (select) {
            select.innerHTML = '<option value="" disabled selected>Select category...</option>';
            policies.forEach(p => {
                activePolicies[p.category] = p;
                const opt = document.createElement("option");
                opt.value = p.category;
                opt.textContent = `${p.category} (Max $${p.max_amount.toFixed(2)})`;
                select.appendChild(opt);
            });
        }
    } catch (err) {
        console.error("Error loading policies:", err);
    }
}

// Update hints and trigger inline validation when category changes
function onCategoryChanged() {
    const category = document.getElementById("category").value;
    const policy = activePolicies[category];
    const catHint = document.getElementById("categoryHint");
    
    if (policy && catHint) {
        catHint.innerHTML = `<strong>Rule:</strong> Max <strong>$${policy.max_amount.toFixed(2)}</strong> &bull; Max <strong>${policy.max_days_old} days</strong> old &bull; Receipt required over <strong>$${policy.receipt_required_above.toFixed(2)}</strong>`;
        catHint.style.color = "var(--primary)";
    }
    triggerInlineValidation();
}

function onAmountChanged() {
    triggerInlineValidation();
}

function onDateChanged() {
    triggerInlineValidation();
}

async function onReceiptChanged() {
    triggerInlineValidation();

    const fileInput = document.getElementById("receipt");
    const file = fileInput?.files[0];
    if (!file) return;

    // Check if image for OCR
    const isImage = /\.(png|jpg|jpeg|webp)$/i.test(file.name);
    if (!isImage) return;

    const ocrBox = document.getElementById("ocrStatusBox");
    const ocrMsg = document.getElementById("ocrStatusMessage");
    const ocrBadge = document.getElementById("ocrConfidenceBadge");
    const ocrDetails = document.getElementById("ocrExtractedDetails");

    if (ocrBox) {
        ocrBox.style.display = "block";
        ocrBox.className = "ocr-status-box ocr-scanning";
        ocrMsg.innerHTML = "<span>⏳ Scanning receipt with Tesseract OCR to auto-fill details...</span>";
        ocrBadge.className = "badge badge-info";
        ocrBadge.textContent = "Processing...";
        if (ocrDetails) ocrDetails.style.display = "none";
    }

    try {
        const formData = new FormData();
        formData.append("receipt", file);

        const res = await fetch("/api/ocr/extract", {
            method: "POST",
            body: formData
        });

        if (!res.ok) throw new Error("OCR request failed");
        const ocr = await res.json();

        if (ocrBox && ocrMsg) {
            const conf = ocr.confidence || {};
            const ext = ocr.extracted || {};

            if (ocr.low_confidence) {
                // Low confidence fallback
                ocrBox.className = "ocr-status-box ocr-warning";
                ocrBadge.className = "badge badge-warning";
                ocrBadge.textContent = `Low Confidence (${Math.round(conf.overall * 100)}%)`;
                ocrMsg.innerHTML = `⚠️ <strong>OCR could not reliably read all fields:</strong> ${escapeHtml(ocr.message)} Please verify and enter details manually.`;
                
                // If amount or date was found despite low overall score, fill them with notice
                if (ext.amount) {
                    document.getElementById("amount").value = ext.amount.toFixed(2);
                }
                if (ext.date) {
                    document.getElementById("expense_date").value = ext.date;
                }
            } else {
                // High or Medium confidence: auto-fill form fields
                ocrBox.className = "ocr-status-box ocr-success";
                ocrBadge.className = conf.level === "HIGH" ? "badge badge-success" : "badge badge-info";
                ocrBadge.textContent = `${conf.level} Confidence (${Math.round(conf.overall * 100)}%)`;
                ocrMsg.innerHTML = `✨ <strong>Receipt scanned successfully!</strong> Extracted fields have been auto-filled below. You can review and edit any field before submitting.`;

                // Auto-fill form
                if (ext.amount) {
                    document.getElementById("amount").value = ext.amount.toFixed(2);
                    document.getElementById("ocrPreviewAmount").textContent = `$${ext.amount.toFixed(2)}`;
                }
                if (ext.date) {
                    document.getElementById("expense_date").value = ext.date;
                    document.getElementById("ocrPreviewDate").textContent = ext.date;
                }
                if (ext.category && activePolicies[ext.category]) {
                    document.getElementById("category").value = ext.category;
                    onCategoryChanged();
                    document.getElementById("ocrPreviewCategory").textContent = ext.category;
                }

                // Auto-fill description if empty and merchant found
                const descInput = document.getElementById("description");
                if (descInput && !descInput.value.trim() && ext.merchant) {
                    descInput.value = `Expense at ${ext.merchant}`;
                }

                if (ocrDetails) ocrDetails.style.display = "flex";
            }

            // Immediately run inline validation on new fields
            triggerInlineValidation();
        }
    } catch (err) {
        console.error("OCR scan error:", err);
        if (ocrBox && ocrMsg) {
            ocrBox.className = "ocr-status-box ocr-warning";
            ocrBadge.className = "badge badge-warning";
            ocrBadge.textContent = "Manual Entry";
            ocrMsg.innerHTML = "⚠️ OCR could not scan this file. Please fill out claim fields manually.";
        }
    }
}

// Debounced live policy validation
let validationTimeout = null;
function triggerInlineValidation() {
    clearTimeout(validationTimeout);
    validationTimeout = setTimeout(runInlineValidation, 250);
}

async function runInlineValidation() {
    const category = document.getElementById("category").value;
    const amountVal = parseFloat(document.getElementById("amount").value) || 0;
    const expenseDate = document.getElementById("expense_date").value;
    const receiptFile = document.getElementById("receipt").files[0];
    const hasReceipt = !!receiptFile;

    const feedbackBox = document.getElementById("realtimePolicyBox");
    const checkList = document.getElementById("policyCheckList");

    if (!category || amountVal <= 0) {
        if (feedbackBox) feedbackBox.style.display = "none";
        return;
    }

    try {
        const res = await fetch("/api/claims/validate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                category,
                amount: amountVal,
                expense_date: expenseDate,
                has_receipt: hasReceipt
            })
        });

        if (!res.ok) return;
        const result = await res.json();

        if (feedbackBox && checkList) {
            feedbackBox.style.display = "block";
            checkList.innerHTML = "";

            if (result.is_clean) {
                feedbackBox.className = "policy-feedback-box feedback-clean";
                checkList.innerHTML = `
                    <li class="policy-item-clean">
                        <span class="icon">✅</span>
                        <span><strong>Policy Compliant:</strong> Amount is within the $${result.policy?.max_amount?.toFixed(2) || ''} limit and date is valid.</span>
                    </li>
                `;
            } else {
                feedbackBox.className = "policy-feedback-box feedback-warning";
                result.violations.forEach(v => {
                    const li = document.createElement("li");
                    li.className = `policy-violation-item violation-${v.severity.toLowerCase()}`;
                    li.innerHTML = `
                        <span class="violation-badge">${v.severity}</span>
                        <span class="violation-msg">${v.message}</span>
                    `;
                    checkList.appendChild(li);
                });
            }
        }
    } catch (err) {
        console.error("Inline validation failed:", err);
    }
}

// Handle Form Submission
async function handleClaimSubmit(event) {
    event.preventDefault();
    const form = document.getElementById("claimForm");
    const submitBtn = document.getElementById("submitClaimBtn");
    const alertBox = document.getElementById("submissionAlert");

    const formData = new FormData(form);

    submitBtn.disabled = true;
    submitBtn.innerHTML = "<span>⏳ Submitting & Validating...</span>";
    hideAlert(alertBox);

    try {
        const res = await fetch("/api/claims", {
            method: "POST",
            body: formData
        });

        const data = await res.json();

        if (!res.ok) {
            showAlert(alertBox, data.error || "Submission failed. Please check form fields.", "error");
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>Submit Claim</span>";
            return;
        }

        // Success handling
        let msg = `Claim #${data.claim.id} submitted successfully! Status: <strong>${data.claim.status.replace('_', ' ')}</strong>.`;
        if (data.violations && data.violations.length > 0) {
            msg += `<br>⚠️ <em>Note: ${data.violations.length} policy flag(s) were recorded for manager review.</em>`;
            showAlert(alertBox, msg, "warning");
        } else {
            showAlert(alertBox, msg, "success");
        }

        form.reset();
        setupDateLimits();
        document.getElementById("realtimePolicyBox").style.display = "none";
        document.getElementById("categoryHint").textContent = "Category policy limits will appear here";
        document.getElementById("categoryHint").style.color = "var(--text-muted)";

        // Reload data
        loadMyClaims();
    } catch (err) {
        console.error("Submission error:", err);
        showAlert(alertBox, "Network error occurred while submitting claim.", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "<span>Submit Claim</span>";
    }
}

// Load and render My Claims table
async function loadMyClaims() {
    const tbody = document.getElementById("myClaimsTableBody");
    try {
        const res = await fetch("/api/claims/my");
        if (!res.ok) throw new Error("Failed to load claims");
        const claims = await res.json();

        updateStats(claims);

        if (!claims || claims.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">No expense claims submitted yet. Use the form above to submit your first claim.</td></tr>';
            return;
        }

        tbody.innerHTML = "";
        claims.forEach(c => {
            const tr = document.createElement("tr");

            // Format flags column
            let flagsHtml = '<span class="badge badge-success">✓ Clean</span>';
            if (c.flags && c.flags.length > 0) {
                flagsHtml = c.flags.map(f => 
                    `<span class="badge badge-warning" title="${escapeHtml(f.message)}">⚠️ ${escapeHtml(f.type.replace('_', ' '))}</span>`
                ).join(" ");
            }

            // Receipt preview link
            let receiptHtml = '';
            if (c.receipt_path) {
                receiptHtml = `<a href="${c.receipt_path}" target="_blank" class="receipt-link" title="View attached receipt">📎 View</a>`;
            }

            tr.innerHTML = `
                <td><strong>#${c.id}</strong></td>
                <td><span class="category-pill">${c.category}</span></td>
                <td><strong>$${c.amount.toFixed(2)}</strong></td>
                <td>${c.expense_date}</td>
                <td><span class="badge status-${c.status}">${formatStatus(c.status)}</span></td>
                <td>${flagsHtml}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="openClaimModal(${c.id})">🔍 Details</button>
                    ${receiptHtml}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to fetch claims:", err);
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-error">Failed to load claims. Please refresh.</td></tr>';
    }
}

function updateStats(claims) {
    let total = claims.length;
    let pending = 0;
    let approvedAmt = 0;
    let flagged = 0;

    claims.forEach(c => {
        if (c.status.includes("PENDING")) pending++;
        if (c.status === "APPROVED") approvedAmt += c.amount;
        if (c.flags && c.flags.length > 0) flagged++;
    });

    const elTotal = document.getElementById("statTotalClaims");
    const elPending = document.getElementById("statPendingClaims");
    const elApproved = document.getElementById("statApprovedAmount");
    const elFlagged = document.getElementById("statFlaggedClaims");

    if (elTotal) elTotal.textContent = total;
    if (elPending) elPending.textContent = pending;
    if (elApproved) elApproved.textContent = `$${approvedAmt.toFixed(2)}`;
    if (elFlagged) elFlagged.textContent = flagged;
}

// Modal view for Claim details & audit history
async function openClaimModal(claimId) {
    try {
        const res = await fetch(`/api/claims/${claimId}`);
        if (!res.ok) return;
        const c = await res.json();

        let modal = document.getElementById("claimDetailModal");
        if (!modal) {
            modal = createClaimDetailModal();
        }

        document.getElementById("modalClaimId").textContent = `#${c.id}`;
        document.getElementById("modalCategory").textContent = c.category;
        document.getElementById("modalAmount").textContent = `$${c.amount.toFixed(2)}`;
        document.getElementById("modalDate").textContent = c.expense_date;
        document.getElementById("modalStatus").innerHTML = `<span class="badge status-${c.status}">${formatStatus(c.status)}</span>`;
        document.getElementById("modalDescription").textContent = c.description;

        // Flags container
        const flagsDiv = document.getElementById("modalFlags");
        if (c.flags && c.flags.length > 0) {
            flagsDiv.innerHTML = c.flags.map(f => `
                <div class="alert alert-warning" style="margin-bottom: 0.5rem; padding: 0.5rem 0.75rem;">
                    <strong>${f.type}:</strong> ${escapeHtml(f.message)}
                </div>
            `).join("");
        } else {
            flagsDiv.innerHTML = '<span class="text-muted">No policy violations detected.</span>';
        }

        // Receipt
        const receiptDiv = document.getElementById("modalReceipt");
        if (c.receipt_path) {
            receiptDiv.innerHTML = `<a href="${c.receipt_path}" target="_blank" class="btn btn-sm btn-outline">📎 View Uploaded Receipt</a>`;
        } else {
            receiptDiv.innerHTML = '<span class="text-muted">No receipt attached</span>';
        }

        // History Timeline
        const historyDiv = document.getElementById("modalHistory");
        if (c.history && c.history.length > 0) {
            historyDiv.innerHTML = c.history.map(h => `
                <div class="timeline-entry">
                    <div class="timeline-badge">●</div>
                    <div class="timeline-body">
                        <div class="timeline-header">
                            <strong>${escapeHtml(h.action)}</strong> by <em>${escapeHtml(h.actor_name || 'System')}</em> (${h.actor_role})
                            <span class="timeline-time">${new Date(h.timestamp).toLocaleString()}</span>
                        </div>
                        <div class="timeline-comment">${escapeHtml(h.comment || '')}</div>
                    </div>
                </div>
            `).join("");
        } else {
            historyDiv.innerHTML = '<span class="text-muted">No history entries yet.</span>';
        }

        modal.style.display = "flex";
    } catch (err) {
        console.error("Failed to load claim detail:", err);
    }
}

function closeClaimModal() {
    const modal = document.getElementById("claimDetailModal");
    if (modal) modal.style.display = "none";
}

function createClaimDetailModal() {
    const div = document.createElement("div");
    div.id = "claimDetailModal";
    div.className = "modal-overlay";
    div.innerHTML = `
        <div class="modal-card">
            <div class="modal-header">
                <h3>Claim Details <span id="modalClaimId"></span></h3>
                <button class="modal-close" onclick="closeClaimModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="detail-grid">
                    <div><strong>Category:</strong> <span id="modalCategory"></span></div>
                    <div><strong>Amount:</strong> <span id="modalAmount"></span></div>
                    <div><strong>Expense Date:</strong> <span id="modalDate"></span></div>
                    <div><strong>Status:</strong> <span id="modalStatus"></span></div>
                </div>
                <div style="margin-top: 1rem;">
                    <strong>Business Purpose:</strong>
                    <p id="modalDescription" class="detail-description"></p>
                </div>
                <div style="margin-top: 1rem;">
                    <strong>Policy Flags / Warnings:</strong>
                    <div id="modalFlags" style="margin-top: 0.35rem;"></div>
                </div>
                <div style="margin-top: 1rem;">
                    <strong>Receipt:</strong>
                    <div id="modalReceipt" style="margin-top: 0.35rem;"></div>
                </div>
                <div style="margin-top: 1.5rem;">
                    <strong>Audit History Trail:</strong>
                    <div id="modalHistory" class="timeline-container"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeClaimModal()">Close</button>
            </div>
        </div>
    `;
    document.body.appendChild(div);
    return div;
}

// Helpers
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

function showAlert(el, msg, type) {
    if (!el) return;
    el.className = `alert alert-${type}`;
    el.innerHTML = msg;
    el.style.display = "block";
}

function hideAlert(el) {
    if (el) el.style.display = "none";
}

function resetPolicyCheck() {
    const feedbackBox = document.getElementById("realtimePolicyBox");
    if (feedbackBox) feedbackBox.style.display = "none";
    const catHint = document.getElementById("categoryHint");
    if (catHint) {
        catHint.textContent = "Category policy limits will appear here";
        catHint.style.color = "var(--text-muted)";
    }
}

