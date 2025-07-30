from __future__ import annotations

from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    UserMixin,
)
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

login_manager = LoginManager()
login_manager.login_view = "auth.login"


auth_bp = Blueprint("auth", __name__)


def _load_credentials() -> tuple[str | None, str | None]:
    env = dotenv_values(ENV_FILE)
    return env.get("DASHBOARD_USERNAME"), env.get("DASHBOARD_PASSWORD")


class User(UserMixin):
    def __init__(self, username: str):
        self.id = username
        self.username = username


@login_manager.user_loader
def load_user(user_id: str):
    username, _ = _load_credentials()
    if user_id == username:
        return User(user_id)
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        stored_user, stored_pass = _load_credentials()
        if username == stored_user and password == stored_pass:
            login_user(User(username))
            next_page = request.args.get("next") or url_for("show_portfolio")
            return redirect(next_page)
        return render_template("login.html", error="Invalid credentials"), 401
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
