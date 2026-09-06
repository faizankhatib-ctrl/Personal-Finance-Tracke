"""
Moneta -- Personal Finance Tracker
A small Flask app with real accounts, hashed passwords, a SQLite
database, and a JSON API that the dashboard's JavaScript talks to.
"""
import os
from datetime import datetime, date

from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Transaction

# Every category the app understands, and whether it belongs under
# income or expense. The same dictionary is sent to the browser so the
# frontend never has to duplicate this list.
CATEGORY_META = {
    "salary":        {"label": "Salary",            "icon": "fa-sack-dollar",         "color": "#33C17B", "type": "income"},
    "freelance":     {"label": "Freelance",         "icon": "fa-laptop-code",         "color": "#2FB6C4", "type": "income"},
    "business":      {"label": "Business",          "icon": "fa-briefcase",           "color": "#8C6FE6", "type": "income"},
    "investment":    {"label": "Investment",        "icon": "fa-chart-line",          "color": "#E7B84E", "type": "income"},
    "gift":          {"label": "Gift",              "icon": "fa-gift",                "color": "#E36FA0", "type": "income"},
    "other_income":  {"label": "Other",             "icon": "fa-circle-plus",         "color": "#7C8AA5", "type": "income"},
    "food":          {"label": "Food & Dining",     "icon": "fa-utensils",            "color": "#FF6B5E", "type": "expense"},
    "transport":     {"label": "Transport",         "icon": "fa-car",                 "color": "#3E8EDE", "type": "expense"},
    "shopping":      {"label": "Shopping",          "icon": "fa-bag-shopping",        "color": "#E7B84E", "type": "expense"},
    "bills":         {"label": "Bills & Utilities", "icon": "fa-file-invoice-dollar", "color": "#E14F42", "type": "expense"},
    "entertainment": {"label": "Entertainment",     "icon": "fa-film",                "color": "#8C6FE6", "type": "expense"},
    "health":        {"label": "Health",            "icon": "fa-heart-pulse",         "color": "#F2668B", "type": "expense"},
    "education":     {"label": "Education",         "icon": "fa-graduation-cap",      "color": "#2FB6C4", "type": "expense"},
    "other_expense": {"label": "Other",             "icon": "fa-ellipsis",            "color": "#7C8AA5", "type": "expense"},
}


def create_app():
    app = Flask(__name__)

    # In production, always set a real SECRET_KEY as an environment
    # variable -- never commit one to source control.
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-key-change-this-in-production"
    )
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        basedir, "moneta.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Cookies only travel over plain HTTP during local development.
    # Flip SESSION_COOKIE_SECURE to True once the app is served over HTTPS.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "error"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ---------------------------------------------------------------
    # Auth routes
    # ---------------------------------------------------------------
    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")

            if not name or not email or not password:
                flash("Please fill in every field.", "error")
                return render_template("signup.html", name=name, email=email)
            if "@" not in email or "." not in email.split("@")[-1]:
                flash("Enter a valid email address.", "error")
                return render_template("signup.html", name=name, email=email)
            if len(password) < 8:
                flash("Password must be at least 8 characters long.", "error")
                return render_template("signup.html", name=name, email=email)
            if password != confirm:
                flash("Passwords do not match.", "error")
                return render_template("signup.html", name=name, email=email)
            if User.query.filter_by(email=email).first():
                flash("An account with this email already exists.", "error")
                return render_template("signup.html", name=name, email=email)

            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
            )
            db.session.add(user)
            db.session.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("signup.html", name="", email="")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            remember = bool(request.form.get("remember"))

            user = User.query.filter_by(email=email).first()
            # Checking the hash only after confirming a user exists keeps
            # the error message identical either way, so a login attempt
            # can't be used to discover which emails are registered.
            if user is None or not check_password_hash(user.password_hash, password):
                flash("Incorrect email or password.", "error")
                return render_template("login.html", email=email)

            login_user(user, remember=remember)
            return redirect(url_for("dashboard"))

        return render_template("login.html", email="")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    # ---------------------------------------------------------------
    # Dashboard (server-rendered shell; data loads via the API below)
    # ---------------------------------------------------------------
    @app.route("/")
    @login_required
    def dashboard():
        return render_template(
            "dashboard.html", user=current_user, categories=CATEGORY_META
        )

    # ---------------------------------------------------------------
    # JSON API -- everything here is scoped to current_user, so one
    # account can never see or touch another account's data.
    # ---------------------------------------------------------------
    @app.route("/api/summary")
    @login_required
    def api_summary():
        rows = Transaction.query.filter_by(user_id=current_user.id).all()
        income = sum(t.amount for t in rows if t.type == "income")
        expense = sum(t.amount for t in rows if t.type == "expense")
        return jsonify(
            {
                "income": income,
                "expense": expense,
                "balance": income - expense,
                "threshold": current_user.alert_threshold,
            }
        )

    @app.route("/api/transactions", methods=["GET"])
    @login_required
    def get_transactions():
        rows = (
            Transaction.query.filter_by(user_id=current_user.id)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .all()
        )
        return jsonify([t.to_dict() for t in rows])

    @app.route("/api/transactions", methods=["POST"])
    @login_required
    def add_transaction():
        data = request.get_json(silent=True) or {}
        t_type = data.get("type")
        category = data.get("category")
        amount = data.get("amount")
        note = (data.get("note") or "").strip()[:255]
        raw_date = data.get("date")

        if t_type not in ("income", "expense"):
            return jsonify({"error": "Invalid transaction type."}), 400
        if category not in CATEGORY_META or CATEGORY_META[category]["type"] != t_type:
            return jsonify({"error": "Invalid category for this type."}), 400
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"error": "Enter a valid amount greater than zero."}), 400
        try:
            parsed_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            parsed_date = date.today()

        txn = Transaction(
            user_id=current_user.id,
            type=t_type,
            category=category,
            amount=amount,
            note=note,
            date=parsed_date,
        )
        db.session.add(txn)
        db.session.commit()
        return jsonify(txn.to_dict()), 201

    @app.route("/api/transactions/<int:txn_id>", methods=["DELETE"])
    @login_required
    def delete_transaction(txn_id):
        txn = Transaction.query.filter_by(id=txn_id, user_id=current_user.id).first()
        if not txn:
            return jsonify({"error": "Transaction not found."}), 404
        db.session.delete(txn)
        db.session.commit()
        return jsonify({"success": True})

    @app.route("/api/threshold", methods=["POST"])
    @login_required
    def update_threshold():
        data = request.get_json(silent=True) or {}
        try:
            threshold = float(data.get("threshold"))
            if threshold < 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid threshold."}), 400
        current_user.alert_threshold = threshold
        db.session.commit()
        return jsonify({"success": True, "threshold": threshold})

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    # debug=True is for local development only -- turn it off before
    # deploying anywhere public.
    app.run(debug=True)
