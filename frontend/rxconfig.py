"""Reflex configuration."""
import reflex as rx

config = rx.Config(
    app_name="frontend",
    frontend_port=3000,
    backend_port=3001,
    db_url="sqlite:///reflex.db",
)
