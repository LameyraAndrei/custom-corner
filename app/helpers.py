import functools
import json
import random
import string
import os
import base64
import uuid
from flask import session, redirect, url_for, flash, request, current_app

from . import db


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.query("SELECT * FROM users WHERE id = ?", (uid,), one=True)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user["is_admin"]:
            flash("Admin access required.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def cart_count(user_id):
    row = db.query(
        "SELECT COALESCE(SUM(quantity),0) AS c FROM cart_items WHERE user_id = ?",
        (user_id,), one=True
    )
    return row["c"] if row else 0


def cart_total(user_id):
    rows = db.query("SELECT * FROM cart_items WHERE user_id = ?", (user_id,))
    total = 0.0
    for r in rows:
        total += (r["unit_price"] + r["customization_fee"]) * r["quantity"]
    return total


def calculate_customization_fee(design_data):
    """Derive the customization fee from the design's element data.
    Text elements add a small fee, image elements add a larger fee --
    this keeps pricing tied to actual design complexity rather than a flat
    hardcoded number.
    """
    if not design_data:
        return 0.0
    try:
        data = json.loads(design_data) if isinstance(design_data, str) else design_data
    except (json.JSONDecodeError, TypeError):
        return 0.0
    fee = 0.0
    for side in ("front", "back"):
        for el in data.get(side, []):
            if el.get("type") == "text":
                fee += 30.0
            elif el.get("type") == "image":
                fee += 70.0
    return fee


def generate_order_number():
    date_part = "".join(random.choices(string.digits, k=0))
    from datetime import datetime
    return "CC-" + datetime.now().strftime("%Y%m%d") + "-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=5)
    )


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_data_url_image(data_url, prefix="design"):
    """Save a base64 data: URL (from the canvas customizer) to the uploads
    folder and return its relative static path. Returns None on failure."""
    if not data_url or not data_url.startswith("data:image"):
        return None
    try:
        header, encoded = data_url.split(",", 1)
        ext = "png"
        if "jpeg" in header:
            ext = "jpg"
        raw = base64.b64decode(encoded)
        if len(raw) > current_app.config["MAX_CONTENT_LENGTH"]:
            return None
        fname = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
        with open(path, "wb") as f:
            f.write(raw)
        return f"uploads/{fname}"
    except Exception:
        return None


STATUS_STEPS = [
    "Pending",
    "Design Review",
    "Confirmed",
    "In Production",
    "Ready",
    "Shipped",
    "Completed",
]

TRACKER_STEPS = [
    ("Pending", "Order Placed"),
    ("Design Review", "Design Confirmed"),
    ("In Production", "In Production"),
    ("Ready", "Ready"),
    ("Shipped", "Shipped"),
    ("Completed", "Delivered"),
]


def status_index(status):
    order = [s[0] for s in TRACKER_STEPS]
    try:
        return order.index(status)
    except ValueError:
        return 0
