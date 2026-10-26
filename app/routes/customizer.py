import json
from flask import Blueprint, render_template, request, jsonify, abort

from .. import db
from ..helpers import login_required, current_user, calculate_customization_fee, save_data_url_image, allowed_file
import os
import uuid
from flask import current_app

bp = Blueprint("customizer", __name__)


@bp.route("/customize/<slug>")
def studio(slug):
    product = db.query(
        "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON c.id = p.category_id "
        "WHERE p.slug = ?", (slug,), one=True,
    )
    if product is None:
        return render_template("404.html"), 404
    colors = db.query("SELECT * FROM product_colors WHERE product_id = ?", (product["id"],))
    sizes = db.query("SELECT * FROM product_sizes WHERE product_id = ?", (product["id"],))

    design = None
    design_id = request.args.get("design_id", type=int)
    if design_id:
        user = current_user()
        if user:
            design = db.query(
                "SELECT * FROM designs WHERE id = ? AND user_id = ?", (design_id, user["id"]), one=True
            )

    return render_template(
        "customizer.html", product=product, colors=colors, sizes=sizes, design=design
    )


@bp.route("/api/designs", methods=["POST"])
@login_required
def save_design():
    """Save (or update) a design. Body: JSON with product_id, name, color,
    size, design_data (the full scene graph), preview_image (data URL)."""
    user = current_user()
    payload = request.get_json(force=True, silent=True) or {}

    product_id = payload.get("product_id")
    if not product_id or not db.query("SELECT id FROM products WHERE id = ?", (product_id,), one=True):
        return jsonify({"ok": False, "error": "Invalid product."}), 400

    design_data = payload.get("design_data") or {"front": [], "back": []}
    design_json = json.dumps(design_data)
    name = (payload.get("name") or "Untitled Design").strip()[:80]
    color = payload.get("color", "")
    size = payload.get("size", "")

    preview_path = None
    preview_data_url = payload.get("preview_image")
    if preview_data_url:
        preview_path = save_data_url_image(preview_data_url, prefix="preview")

    design_id = payload.get("design_id")
    if design_id:
        existing = db.query("SELECT * FROM designs WHERE id = ? AND user_id = ?", (design_id, user["id"]), one=True)
        if not existing:
            return jsonify({"ok": False, "error": "Design not found."}), 404
        db.execute(
            "UPDATE designs SET name=?, color=?, size=?, design_data=?, "
            "preview_image=COALESCE(?, preview_image), updated_at=datetime('now') WHERE id=?",
            (name, color, size, design_json, preview_path, design_id),
        )
    else:
        design_id = db.execute(
            "INSERT INTO designs (user_id, product_id, name, color, size, design_data, preview_image) "
            "VALUES (?,?,?,?,?,?,?)",
            (user["id"], product_id, name, color, size, design_json, preview_path),
        )

    design = db.query("SELECT * FROM designs WHERE id = ?", (design_id,), one=True)
    return jsonify({"ok": True, "design_id": design_id, "preview_image": design["preview_image"]})


@bp.route("/api/designs/<int:design_id>", methods=["GET"])
@login_required
def get_design(design_id):
    user = current_user()
    design = db.query("SELECT * FROM designs WHERE id = ? AND user_id = ?", (design_id, user["id"]), one=True)
    if not design:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({
        "ok": True,
        "design": {
            "id": design["id"], "product_id": design["product_id"], "name": design["name"],
            "color": design["color"], "size": design["size"],
            "design_data": json.loads(design["design_data"]),
            "preview_image": design["preview_image"],
        }
    })


@bp.route("/api/designs/<int:design_id>", methods=["DELETE"])
@login_required
def delete_design(design_id):
    user = current_user()
    design = db.query("SELECT * FROM designs WHERE id = ? AND user_id = ?", (design_id, user["id"]), one=True)
    if not design:
        return jsonify({"ok": False, "error": "Not found"}), 404
    db.execute("DELETE FROM designs WHERE id = ?", (design_id,))
    return jsonify({"ok": True})


@bp.route("/api/upload-image", methods=["POST"])
@login_required
def upload_image():
    """Accept an uploaded image file for use as a design element and return
    it as a base64 data URL (kept in-browser/in the design JSON -- simplest
    and most portable for a student project's saved-design reconstruction)."""
    file = request.files.get("image")
    if not file or file.filename == "":
        return jsonify({"ok": False, "error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"ok": False, "error": "Unsupported file type. Use PNG, JPG, GIF or WEBP."}), 400

    raw = file.read()
    if len(raw) > current_app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"ok": False, "error": "Image is too large (max 6MB)."}), 400

    import base64
    ext = file.filename.rsplit(".", 1)[-1].lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    data_url = f"data:image/{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    # Also persist a copy server-side (uploads folder) for admin/inventory review.
    fname = f"upload_{uuid.uuid4().hex[:12]}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
    with open(path, "wb") as f:
        f.write(raw)

    return jsonify({"ok": True, "data_url": data_url, "static_path": f"uploads/{fname}"})
