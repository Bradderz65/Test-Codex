from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-me-please"),
    ENABLE_GIT_SYNC=os.environ.get("ENABLE_GIT_SYNC", "1") == "1",
    GIT_AUTO_PUSH=os.environ.get("GIT_AUTO_PUSH", "0") == "1",
    GIT_REMOTE_NAME=os.environ.get("GIT_REMOTE_NAME", "origin"),
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10 MB
)

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, fallback):
    if not path.exists():
        path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
        return json.loads(json.dumps(fallback))
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError:
        app.logger.warning("Corrupted JSON detected in %s; resetting.", path)
        path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
        return json.loads(json.dumps(fallback))


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_users() -> Dict[str, Dict[str, str]]:
    data = _read_json(DATA_DIR / "users.json", {"users": {}})
    return data.get("users", {})


def save_users(users: Dict[str, Dict[str, str]]) -> None:
    _write_json(DATA_DIR / "users.json", {"users": users})


def get_photos() -> List[Dict[str, str]]:
    data = _read_json(DATA_DIR / "photos.json", {"photos": []})
    photos = data.get("photos", [])

    updated = False
    for photo in photos:
        if "id" not in photo:
            photo["id"] = uuid4().hex
            updated = True

    if updated:
        save_photos(photos)

    return photos


def save_photos(photos: List[Dict[str, str]]) -> None:
    _write_json(DATA_DIR / "photos.json", {"photos": photos})


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def format_timestamp(raw_value: str | None) -> str:
    if not raw_value:
        return ""

    value = str(raw_value)
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        cleaned = value.replace("T", " ")
        if "." in cleaned:
            cleaned = cleaned.split(".", 1)[0]
        return cleaned


def current_username() -> str | None:
    return session.get("username")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_username():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.url))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_user():
    return {"current_username": current_username()}


def auto_commit(paths: List[Path], message: str) -> None:
    if not app.config.get("ENABLE_GIT_SYNC", False):
        return

    repo_root = BASE_DIR
    git_paths = []
    for path in paths:
        try:
            git_paths.append(str(path.relative_to(repo_root)))
        except ValueError:
            git_paths.append(str(path))

    try:
        for git_path in git_paths:
            subprocess.run(["git", "add", git_path], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo_root
        )
        if diff.returncode == 0:
            return
        subprocess.run(["git", "commit", "-m", message], cwd=repo_root, check=True)
        if app.config.get("GIT_AUTO_PUSH"):
            subprocess.run(["git", "push", app.config.get("GIT_REMOTE_NAME", "origin")], cwd=repo_root, check=True)
    except FileNotFoundError:
        app.logger.warning("Git is not available; skipping sync.")
    except subprocess.CalledProcessError as exc:
        app.logger.warning("Git sync failed: %s", exc)


@app.route("/")
def index():
    sorted_photos = sorted(
        get_photos(), key=lambda item: item.get("uploaded_at", ""), reverse=True
    )
    enriched_photos = [
        {
            **photo,
            "display_time": format_timestamp(photo.get("uploaded_at")),
        }
        for photo in sorted_photos
    ]
    return render_template("index.html", photos=enriched_photos)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        users = get_users()
        if username in users:
            flash("This username is already taken.", "warning")
            return redirect(url_for("register"))

        users[username] = {"password_hash": generate_password_hash(password)}
        save_users(users)
        auto_commit([DATA_DIR / "users.json"], f"Add user {username}")

        user_upload_dir = UPLOADS_DIR / username
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        session["username"] = username
        flash("Account created! Start sharing your photos.", "success")
        return redirect(url_for("upload"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users = get_users()

        if username not in users or not check_password_hash(users[username]["password_hash"], password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))

        session["username"] = username
        flash("Welcome back!", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("upload"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    username = current_username()
    assert username is not None

    if request.method == "POST":
        uploaded = request.files.get("photo")
        caption = request.form.get("caption", "").strip()

        if not uploaded or uploaded.filename == "":
            flash("Please choose an image to upload.", "warning")
            return redirect(url_for("upload"))
        if not allowed_file(uploaded.filename):
            flash("Unsupported file type.", "danger")
            return redirect(url_for("upload"))

        user_dir = UPLOADS_DIR / username
        user_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        filename = secure_filename(uploaded.filename)
        stored_name = f"{timestamp}_{filename}"
        file_path = user_dir / stored_name
        uploaded.save(file_path)

        photos = get_photos()
        photo_entry = {
            "id": uuid4().hex,
            "user": username,
            "caption": caption,
            "static_path": str(Path("uploads") / username / stored_name).replace(os.sep, "/"),
            "uploaded_at": datetime.utcnow().isoformat(),
        }
        photos.append(photo_entry)
        save_photos(photos)

        auto_commit([file_path, DATA_DIR / "photos.json"], f"Add photo by {username}")

        flash("Photo uploaded successfully!", "success")
        return redirect(url_for("index"))

    user_photos = [
        {
            **photo,
            "display_time": format_timestamp(photo.get("uploaded_at")),
        }
        for photo in get_photos()
        if photo.get("user") == username
    ]
    user_photos.sort(key=lambda item: item.get("uploaded_at", ""), reverse=True)

    return render_template("upload.html", user_photos=user_photos)


@app.post("/photos/<photo_id>/delete")
@login_required
def delete_photo(photo_id: str):
    username = current_username()
    assert username is not None

    photos = get_photos()
    target = next((photo for photo in photos if photo.get("id") == photo_id), None)

    if not target:
        flash("That photo could not be found.", "warning")
        return redirect(url_for("upload"))

    if target.get("user") != username:
        flash("You can only delete photos you uploaded.", "danger")
        return redirect(url_for("upload"))

    static_rel = target.get("static_path")
    file_path: Path | None = None
    if static_rel:
        file_path = BASE_DIR / "static" / Path(static_rel)
        if file_path.exists():
            file_path.unlink()

    updated_photos = [photo for photo in photos if photo.get("id") != photo_id]
    save_photos(updated_photos)

    paths_to_commit = [DATA_DIR / "photos.json"]
    if file_path is not None:
        paths_to_commit.append(file_path)
    auto_commit(paths_to_commit, f"Remove photo by {username}")

    flash("Photo deleted.", "info")
    return redirect(url_for("upload"))


@app.errorhandler(413)
def handle_large_file(_):
    flash("File is too large. Maximum size is 10 MB.", "danger")
    return redirect(url_for("upload"))


if __name__ == "__main__":
    app.run(debug=True)
