"""Seed the database with realistic sample data so the app is demoable
immediately after first run."""
import os
from werkzeug.security import generate_password_hash
from . import db


def run_seed(app):
    with app.app_context():
        conn = db.get_db()
        cur = conn.cursor()

        # --- Users ---------------------------------------------------
        cur.execute(
            "INSERT INTO users (name, email, phone, password_hash, is_admin) VALUES (?,?,?,?,1)",
            ("Custom Corner Admin", "admin@customcorner.ph", "0917 000 0000",
             generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123"))),
        )
        cur.execute(
            "INSERT INTO users (name, email, phone, password_hash, is_admin) VALUES (?,?,?,?,0)",
            ("Maria Santos", "maria@example.com", "0917 123 4567",
             generate_password_hash("password123")),
        )
        maria_id = cur.lastrowid

        cur.execute(
            "INSERT INTO addresses (user_id, label, full_name, phone, address_line, city, province, postal_code, is_default) "
            "VALUES (?,?,?,?,?,?,?,?,1)",
            (maria_id, "Home", "Maria Santos", "0917 123 4567",
             "123 Kalayaan Ave, Brgy. Pinagkaisahan", "Quezon City", "Metro Manila", "1105"),
        )

        # --- Categories ------------------------------------------------
        categories = [
            ("T-Shirts", "t-shirts", "checkroom"),
            ("Mugs", "mugs", "coffee"),
            ("Tote Bags", "tote-bags", "shopping_bag"),
            ("Keychains", "keychains", "key"),
            ("Stickers", "stickers", "auto_awesome"),
            ("Phone Cases", "phone-cases", "smartphone"),
        ]
        cat_ids = {}
        for name, slug, icon in categories:
            cur.execute("INSERT INTO categories (name, slug, icon) VALUES (?,?,?)", (name, slug, icon))
            cat_ids[slug] = cur.lastrowid

        # --- Products ----------------------------------------------------
        products = [
            dict(cat="t-shirts", name="Heavyweight Cotton Tee", slug="heavyweight-cotton-tee",
                 desc="A boxy, heavyweight 100% ring-spun cotton tee (240gsm) with a soft-touch finish. "
                      "The blank canvas for screenprint, direct-to-film, or embroidered personalization.",
                 price=350, fee=100, image="tshirt.jpg", material="100% Ring-spun Cotton, 240gsm",
                 prod_time="2-4 business days", shape="tshirt", back=1, stock=120, featured=1,
                 colors=[("Natural Sand", "#E8DFD1"), ("Charcoal", "#3A3632"), ("Off-White", "#FAF8F5"), ("Sage", "#7C8B72")],
                 sizes=["XS", "S", "M", "L", "XL", "XXL"]),
            dict(cat="mugs", name="Speckled Ceramic Mug", slug="speckled-ceramic-mug",
                 desc="An 11oz Scandinavian-style speckled ceramic mug with a warm cream glaze. "
                      "Dishwasher and microwave safe. Perfect for monograms and small illustrations.",
                 price=180, fee=80, image="mug.jpg", material="Glazed Ceramic, 11oz",
                 prod_time="2-3 business days", shape="mug", back=0, stock=200, featured=1,
                 colors=[("Cream", "#F4EFEA"), ("Espresso", "#3A302A"), ("Sage", "#7C8B72")],
                 sizes=[]),
            dict(cat="tote-bags", name="Organic Canvas Tote", slug="organic-canvas-tote",
                 desc="A heavyweight organic cotton canvas tote bag in a natural oatmeal finish, with "
                      "reinforced stitched handles. Great for embroidered monograms or bold print designs.",
                 price=250, fee=90, image="tote.jpg", material="12oz Organic Cotton Canvas",
                 prod_time="2-4 business days", shape="tote", back=0, stock=150, featured=1,
                 colors=[("Oatmeal", "#E3D8C8"), ("Black", "#201B14"), ("Clay", "#C29B78")],
                 sizes=[]),
            dict(cat="keychains", name="Acrylic Arch Keychain", slug="acrylic-arch-keychain",
                 desc="A crystal-clear cast acrylic keychain, laser-cut into a soft arch silhouette. "
                      "Add initials, small text, or a mini illustration.",
                 price=80, fee=40, image="keychain.jpg", material="3mm Cast Acrylic",
                 prod_time="1-2 business days", shape="keychain", back=0, stock=300, featured=1,
                 colors=[("Clear", "#F4EFEA"), ("Frosted", "#E8E3DC")],
                 sizes=[]),
            dict(cat="stickers", name="Die-Cut Vinyl Sticker Pack", slug="die-cut-vinyl-sticker",
                 desc="Waterproof, UV-resistant die-cut vinyl stickers. Upload your own artwork or add "
                      "custom text for a set of 3-inch stickers.",
                 price=30, fee=30, image="sticker.jpg", material="Waterproof Vinyl",
                 prod_time="1-2 business days", shape="sticker", back=0, stock=500, featured=0,
                 colors=[("Glossy", "#FFFFFF"), ("Matte", "#F4EFEA")],
                 sizes=[]),
            dict(cat="phone-cases", name="Slim Matte Phone Case", slug="slim-matte-phone-case",
                 desc="A slim-fit matte polycarbonate phone case with reinforced corners. Personalize "
                      "with photos, monograms, or full-wrap artwork.",
                 price=300, fee=100, image="phonecase.jpg", material="Polycarbonate + TPU bumper",
                 prod_time="2-3 business days", shape="phonecase", back=0, stock=180, featured=0,
                 colors=[("Charcoal", "#3A3632"), ("Clear", "#F4EFEA"), ("Sand", "#E8DFD1")],
                 sizes=["iPhone 13/14", "iPhone 15", "iPhone 15 Pro", "Samsung S23"]),
        ]

        for p in products:
            cur.execute(
                "INSERT INTO products (category_id, name, slug, description, base_price, customization_fee, "
                "image, material, production_time, mockup_shape, has_back_side, stock, is_active, is_featured) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
                (cat_ids[p["cat"]], p["name"], p["slug"], p["desc"], p["price"], p["fee"], p["image"],
                 p["material"], p["prod_time"], p["shape"], p["back"], p["stock"], p["featured"]),
            )
            pid = cur.lastrowid
            for cname, chex in p["colors"]:
                cur.execute("INSERT INTO product_colors (product_id, name, hex) VALUES (?,?,?)", (pid, cname, chex))
            for sname in p["sizes"]:
                cur.execute("INSERT INTO product_sizes (product_id, name) VALUES (?,?)", (pid, sname))

        conn.commit()

        # --- A sample saved design + order so Account/Admin aren't empty --
        import json as _json
        sample_design = {
            "front": [
                {"id": "el1", "type": "text", "text": "Happy Birthday!", "x": 300, "y": 260, "w": 220, "h": 40,
                 "rotation": 0, "font": "Playfair Display", "size": 32, "color": "#2B2623",
                 "bold": True, "italic": False, "align": "center"}
            ],
            "back": []
        }
        tshirt = db.query("SELECT id, base_price, customization_fee FROM products WHERE slug='heavyweight-cotton-tee'", one=True)
        cur.execute(
            "INSERT INTO designs (user_id, product_id, name, color, size, design_data, preview_image) "
            "VALUES (?,?,?,?,?,?,?)",
            (maria_id, tshirt["id"], "Birthday Tee for Ana", "Natural Sand", "M", _json.dumps(sample_design), None),
        )
        design_id = cur.lastrowid
        conn.commit()

        cur.execute(
            "INSERT INTO orders (user_id, order_number, status, subtotal, delivery_fee, total, full_name, email, "
            "phone, address_line, city, province, postal_code, delivery_option, payment_method) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (maria_id, "CC-20260910-A1B2C", "In Production", 450.0, 80.0, 530.0, "Maria Santos",
             "maria@example.com", "0917 123 4567", "123 Kalayaan Ave, Brgy. Pinagkaisahan",
             "Quezon City", "Metro Manila", "1105", "Standard", "GCash"),
        )
        order_id = cur.lastrowid
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, design_id, product_name, color, size, quantity, "
            "unit_price, customization_fee, design_data) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (order_id, tshirt["id"], design_id, "Heavyweight Cotton Tee", "Natural Sand", "M", 1,
             tshirt["base_price"], 100.0, _json.dumps(sample_design)),
        )
        conn.commit()
        print("Database seeded successfully.")
