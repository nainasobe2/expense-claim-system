import os
from datetime import timedelta
from flask import Flask, jsonify, render_template, send_from_directory, redirect, url_for, session
from config import Config
from models import db, User, Policy, Claim, ClaimHistory
from routes.auth_routes import auth_bp, login_required, role_required, get_role_redirect_url
from routes.claim_routes import claim_bp
from routes.approval_routes import approval_bp
from routes.analytics_routes import finance_bp

def create_app(config_class=Config):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_class)

    # Session security settings
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=1)

    # Ensure uploads directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(claim_bp)
    app.register_blueprint(approval_bp)
    app.register_blueprint(finance_bp)

    # Context processor to inject current user into all Jinja templates
    @app.context_processor
    def inject_user():
        if "user_id" in session:
            return {
                "current_user": {
                    "id": session.get("user_id"),
                    "name": session.get("name"),
                    "email": session.get("email"),
                    "role": session.get("role"),
                    "department": session.get("department")
                }
            }
        return {"current_user": None}

    # Health check & database connection test endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        try:
            result = db.session.execute(db.text("SELECT VERSION() AS version")).fetchone()
            user_count = User.query.count()
            policy_count = Policy.query.count()
            claim_count = Claim.query.count()
            
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "mysql_version": result[0] if result else "unknown",
                "counts": {
                    "users": user_count,
                    "policies": policy_count,
                    "claims": claim_count
                }
            }), 200
        except Exception as e:
            return jsonify({
                "status": "error",
                "database": "disconnected",
                "error": str(e)
            }), 500

    # Root redirect
    @app.route("/", methods=["GET"])
    def index():
        if "user_id" in session:
            return redirect(get_role_redirect_url(session.get("role")))
        return redirect(url_for("login"))

    # Login page
    @app.route("/login", methods=["GET"])
    def login():
        if "user_id" in session:
            return redirect(get_role_redirect_url(session.get("role")))
        return render_template("login.html")

    # Logout page redirect
    @app.route("/logout", methods=["GET"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # Role Protected Dashboards
    @app.route("/employee", methods=["GET"])
    @login_required
    @role_required("EMPLOYEE", "FINANCE_ADMIN")
    def employee_dashboard():
        return render_template("employee.html")

    @app.route("/approver", methods=["GET"])
    @login_required
    @role_required("MANAGER", "FINANCE_ADMIN")
    def approver_dashboard():
        return render_template("approver.html")

    @app.route("/finance", methods=["GET"])
    @login_required
    @role_required("FINANCE_ADMIN")
    def finance_dashboard():
        return render_template("finance.html")

    # Claim Detail Page showing full timeline
    @app.route("/claims/<int:claim_id>", methods=["GET"])
    @login_required
    def claim_detail_page(claim_id):
        user_id = session.get("user_id")
        user_role = session.get("role")
        claim = Claim.query.get_or_404(claim_id)
        
        # Access control: creator, managers, or finance
        if user_role == "EMPLOYEE" and claim.user_id != user_id:
            return redirect(url_for("employee_dashboard"))

        return render_template("claim_detail.html", claim_id=claim_id)

    # Serve uploaded receipts securely
    @app.route("/uploads/<filename>", methods=["GET"])
    @login_required
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
