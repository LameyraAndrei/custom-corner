import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from .. import db
from ..helpers import current_user

bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("main.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if not name:
            errors.append("Full name is required.")
        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if db.query("SELECT id FROM users WHERE email = ?", (email,), one=True):
            errors.append("An account with that email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html", form=request.form)

        uid = db.execute(
            "INSERT INTO users (name, email, phone, password_hash, is_admin) VALUES (?,?,?,?,0)",
            (name, email, phone, generate_password_hash(password)),
        )
        session.clear()
        session["user_id"] = uid
        flash("Welcome to Custom Corner! Your account has been created.", "success")
        return redirect(url_for("main.home"))

    return render_template("auth/register.html", form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("main.home"))

    next_url = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.query("SELECT * FROM users WHERE email = ?", (email,), one=True)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password.", "error")
            return render_template("auth/login.html", email=email, next=next_url)

        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name'].split(' ')[0]}!", "success")
        return redirect(next_url or url_for("main.home"))

    return render_template("auth/login.html", email="", next=next_url)


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))
