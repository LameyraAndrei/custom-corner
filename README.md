# Custom Corner — "Make It Yours."

A full-stack personalized-merchandise e-commerce platform built for a
technopreneurship project. Customers browse a catalog of blank products
(t-shirts, mugs, tote bags, keychains, stickers, phone cases), design them
in a live in-browser **Design Studio**, add the finished design to their
cart, and check out — with an admin dashboard to manage orders, products,
custom designs, customers, inventory, and reports.

The Stitch AI mockups provided for this project were used purely as a
**visual/UX reference** (colors, typography, layout, component language).
The actual application — routing, database, customizer engine, cart,
checkout, and admin tooling — was built from scratch as a proper Flask app.

## Tech Stack

- **Frontend:** HTML5, CSS3 (Tailwind CDN configured with the project's
  design tokens), vanilla JavaScript (no frontend framework).
- **Backend:** Python 3 + Flask (blueprints per feature area).
- **Database:** SQLite via the standard library `sqlite3` module, with all
  queries parameterized. The data-access layer (`app/db.py`) is a thin
  wrapper, so swapping in MySQL/PostgreSQL later mainly means changing the
  connection function, not the rest of the app.
- **Design Studio:** a single `<canvas>` element rendered by
  `static/js/customizer.js`. Product mockups (t-shirt, mug, tote, keychain,
  sticker, phone case) are drawn as vector shapes so changing the product
  color re-renders instantly with no image assets required. A design is
  stored as **data** — a JSON scene graph of text/image elements (position,
  size, rotation, font, color, etc.) — so any saved design can be fully
  reconstructed, not just replayed as a flat screenshot.

## Getting Started

```bash
cd customcorner
pip install -r requirements.txt
python run.py
```

Then open **http://localhost:5000**.

The SQLite database and sample data are created automatically the first
time you run the app (`app/database/custom_corner.sqlite3`). To start over
with a clean database, just delete that file and restart.

### Demo accounts

| Role     | Email                     | Password      |
|----------|---------------------------|---------------|
| Customer | maria@example.com         | password123   |
| Admin    | admin@customcorner.ph     | admin123      |

## Project Structure

```
customcorner/
├── run.py                     # App entry point
├── requirements.txt
└── app/
    ├── __init__.py             # App factory, blueprint registration
    ├── config.py                # Settings (delivery fees, upload limits, etc.)
    ├── db.py                    # SQLite connection helper (parameterized queries)
    ├── seed.py                  # Sample data (categories, products, demo users/orders)
    ├── helpers.py                # Auth decorators, cart totals, pricing, order numbers
    ├── database/
    │   └── schema.sql            # Full relational schema
    ├── routes/
    │   ├── main.py                # Home, How It Works, About
    │   ├── auth.py                # Register / login / logout
    │   ├── shop.py                # Catalog (search/filter/sort) + product detail
    │   ├── customizer.py          # Design Studio page + save/load/upload JSON API
    │   ├── cart.py                # Cart page + add/update/remove JSON API
    │   ├── orders.py              # Checkout, confirmation, order tracking
    │   ├── account.py             # Profile, order history, saved designs, addresses
    │   └── admin.py               # Dashboard, orders, products, designs, customers,
    │                               #   inventory, reports, settings
    ├── templates/                 # Jinja2 templates (mirrors routes/ above)
    ├── static/
    │   ├── css/style.css
    │   ├── js/
    │   │   ├── customizer.js       # Design Studio engine (canvas, drag/resize/rotate,
    │   │   │                       #   undo/redo, price calc, save/add-to-cart)
    │   │   └── main.js             # Site-wide small helpers (flash auto-dismiss)
    │   ├── images/                 # Seed product photos
    │   └── uploads/                # User-uploaded design images + saved previews
    └── database/custom_corner.sqlite3   # created on first run
```

## Database Schema

`users`, `addresses`, `categories`, `products`, `product_colors`,
`product_sizes`, `designs`, `design_elements`, `cart_items`, `orders`,
`order_items` — see `app/database/schema.sql` for full column definitions,
primary/foreign keys, and indexes.

A saved design's authoritative data lives in `designs.design_data` as a
JSON blob (the exact scene graph the customizer renders); `design_elements`
exists for relational completeness/reporting.

## Security Notes

- Passwords are hashed with Werkzeug's `generate_password_hash` /
  `check_password_hash` (never stored in plain text).
- All SQL is parameterized — no string-built queries.
- Server-side validation on registration, checkout, and admin forms (not
  just HTML `required` attributes).
- Session-based authentication; a separate `admin_required` decorator
  gates every `/admin/*` route.
- Uploaded design images are validated by extension and size (max 6MB)
  before being accepted.

## Known Simplifications (by design, for a student project)

- Payment is **simulated** — no real payment gateway is integrated, and
  the checkout page and code say so explicitly.
- Product mockups in the Design Studio are drawn as simplified vector
  shapes rather than photographic mockups, so any color change re-renders
  instantly without needing per-color photo assets.
- Uploaded design images are embedded as base64 data URLs inside the
  saved design JSON (in addition to being copied to `static/uploads/`),
  which keeps "reconstruct a saved design" simple and self-contained.
