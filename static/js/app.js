// Shared application JavaScript

document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
});

async function checkBackendHealth() {
    const badge = document.getElementById("apiStatusBadge");
    if (!badge) return;

    try {
        const res = await fetch("/api/health");
        if (res.ok) {
            const data = await res.json();
            badge.textContent = `● DB: MySQL (${data.mysql_version})`;
            badge.style.color = "#10b981";
        } else {
            badge.textContent = "● DB: Disconnected";
            badge.style.color = "#ef4444";
        }
    } catch (e) {
        badge.textContent = "● API: Offline";
        badge.style.color = "#ef4444";
    }
}

function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `alert alert-${type}`;
    toast.style.marginBottom = "0.5rem";
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4000);
}
