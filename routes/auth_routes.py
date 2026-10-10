from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for
from models import User

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized. Please log in."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Unauthorized. Please log in."}), 401
                return redirect(url_for("login"))
            
            user_role = session.get("role")
            if user_role not in allowed_roles:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": f"Forbidden. Role '{user_role}' does not have access."}), 403
                
                # Redirect to their designated role dashboard
                if user_role == "EMPLOYEE":
                    return redirect(url_for("employee_dashboard"))
                elif user_role == "MANAGER":
                    return redirect(url_for("approver_dashboard"))
                elif user_role == "FINANCE_ADMIN":
                    return redirect(url_for("finance_dashboard"))
                return redirect(url_for("login"))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_role_redirect_url(role: str) -> str:
    if role == "EMPLOYEE":
        return "/employee"
    elif role == "MANAGER":
        return "/approver"
    elif role == "FINANCE_ADMIN":
        return "/finance"
    return "/login"

@auth_bp.route("/api/auth/login", methods=["POST"])
def login_api():
    data = request.get_json(silent=True) or request.form.to_dict()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    # Establish session
    session.permanent = True
    session["user_id"] = user.id
    session["name"] = user.name
    session["email"] = user.email
    session["role"] = user.role
    session["department"] = user.department

    redirect_url = get_role_redirect_url(user.role)

    return jsonify({
        "message": "Login successful.",
        "user": user.to_dict(),
        "redirect_url": redirect_url
    }), 200

@auth_bp.route("/api/auth/logout", methods=["POST", "GET"])
def logout_api():
    session.clear()
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"message": "Logged out successfully."}), 200
    return redirect(url_for("login"))

@auth_bp.route("/api/auth/me", methods=["GET"])
def get_current_user():
    if "user_id" not in session:
        return jsonify({"authenticated": False, "user": None}), 200

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"authenticated": False, "user": None}), 200

    return jsonify({
        "authenticated": True,
        "user": user.to_dict()
    }), 200

@auth_bp.route("/dev/login-as/<role_key>", methods=["GET"])
def dev_quick_login(role_key):
    """
    Convenience helper for automated browser testing and headless demo screenshots.
    """
    role_map = {
        "employee": "employee@example.com",
        "manager": "manager@example.com",
        "finance": "finance@example.com"
    }
    email = role_map.get(role_key.lower())
    if not email:
        return redirect(url_for("login"))

    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for("login"))

    session.permanent = True
    session["user_id"] = user.id
    session["name"] = user.name
    session["email"] = user.email
    session["role"] = user.role
    session["department"] = user.department

    next_url = request.args.get("next")
    if next_url:
        return redirect(next_url)

    return redirect(get_role_redirect_url(user.role))

