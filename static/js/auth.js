// Authentication handlers: form submit, quick login, and error display

async function handleLoginSubmit(event) {
    if (event) event.preventDefault();
    
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const submitBtn = document.getElementById("submitBtn");
    const alertBox = document.getElementById("authAlert");

    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();

    if (!email || !password) {
        showAuthAlert("Please enter both email and password.");
        return;
    }

    setButtonLoading(submitBtn, true, "Signing In...");
    hideAuthAlert();

    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (!response.ok) {
            showAuthAlert(data.error || "Login failed. Please check your credentials.");
            setButtonLoading(submitBtn, false, "Sign In");
            return;
        }

        // Redirect based on role returned by backend
        window.location.href = data.redirect_url || "/";
    } catch (err) {
        console.error("Login request error:", err);
        showAuthAlert("Unable to connect to server. Please ensure the backend is running.");
        setButtonLoading(submitBtn, false, "Sign In");
    }
}

function quickLogin(email, password) {
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    if (emailInput && passwordInput) {
        emailInput.value = email;
        passwordInput.value = password;
        handleLoginSubmit();
    }
}

function showAuthAlert(message) {
    const alertBox = document.getElementById("authAlert");
    if (alertBox) {
        alertBox.textContent = message;
        alertBox.style.display = "block";
    }
}

function hideAuthAlert() {
    const alertBox = document.getElementById("authAlert");
    if (alertBox) {
        alertBox.style.display = "none";
    }
}

function setButtonLoading(btn, isLoading, text) {
    if (!btn) return;
    btn.disabled = isLoading;
    btn.innerHTML = isLoading ? `<span>⏳ ${text}</span>` : `<span>${text}</span>`;
}

