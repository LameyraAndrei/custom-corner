"""
Entry point for the Custom Corner Flask application.

Usage:
    python run.py

The database (SQLite) and sample data are created automatically on first
run if app/database/custom_corner.sqlite3 does not yet exist. To force a
fresh reset, delete that file and restart the app.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="127.0.0.1", port=5000)
