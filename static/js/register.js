// Registration form handler (reuses showAuthAlert/hideAuthAlert/setButtonLoading from auth.js)

async function handleRegisterSubmit(event) {
    if (event) event.preventDefault();

    const submitBtn = document.getElementById("submitBtn");
    const payload = {
        name: document.getElementById("name").value.trim(),
        email: document.getElementById("email").value.trim(),
        department: document.getElementById("department").value.trim(),
        password: document.getElementById("password").value.trim(),
        confirm_password: document.getElementById("confirm_password").value.trim(),
    };

    if (!payload.name || !payload.email || !payload.department || !payload.password || !payload.confirm_password) {
        showAuthAlert("Please fill in all fields.");
        return;
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(payload.email)) {
        showAuthAlert("Please enter a valid email address.");
        return;
    }
    if (payload.password.length < 8) {
        showAuthAlert("Password must be at least 8 characters.");
        return;
    }
    if (payload.password !== payload.confirm_password) {
        showAuthAlert("Passwords do not match.");
        return;
    }

    setButtonLoading(submitBtn, true, "Creating account...");
    hideAuthAlert();

    try {
        const response = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();

        if (!response.ok) {
            showAuthAlert(data.error || "Registration failed. Please try again.");
            setButtonLoading(submitBtn, false, "Create Account");
            return;
        }

        window.location.href = data.redirect_url || "/login?registered=1";
    } catch (err) {
        console.error("Registration request error:", err);
        showAuthAlert("Unable to connect to server. Please ensure the backend is running.");
        setButtonLoading(submitBtn, false, "Create Account");
    }
}
