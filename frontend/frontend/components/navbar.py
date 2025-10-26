"""Navigation bar component."""
import reflex as rx
from frontend.state.auth_state import AuthState


def navbar() -> rx.Component:
    """Render navigation bar."""
    return rx.box(
        rx.hstack(
            # Logo and brand
            rx.hstack(
                rx.image(
                    src="/logo2.png",
                    width="40px",
                    height="40px",
                    alt="RESO Logo"
                ),
                rx.heading("RESO", size="6", color="white"),
                spacing="3",
                align="center"
            ),
            rx.spacer(),
            rx.cond(
                AuthState.is_authenticated,
                rx.hstack(
                    rx.text(AuthState.user_display_name, color="white"),
                    rx.button(
                        "Logout",
                        on_click=AuthState.logout,
                        color_scheme="red",
                        size="2"
                    ),
                    spacing="4"
                ),
                rx.button(
                    "Login",
                    on_click=lambda: rx.redirect("/login"),
                    color_scheme="blue",
                    size="2"
                )
            ),
            align="center",
            width="100%",
            padding="4"
        ),
        bg="blue.600",
        width="100%",
        position="sticky",
        top="0",
        z_index="1000",
        box_shadow="md"
    )
