"""Login page - Supabase authentication."""
import reflex as rx
from frontend.state.auth_state import AuthState


def login_page() -> rx.Component:
    """Modern login page with Supabase auth."""
    return rx.box(
        rx.hstack(
            # Left side - Branding/Hero
            rx.box(
                rx.vstack(
                    rx.heading(
                        "RESO",
                        size="9",
                        color="#FFFFFF",
                        font_weight="700"
                    ),
                    rx.image(
                        src="/logo2.png",
                        width="300px",
                        height="300px",
                        alt="RESO Logo",
                        style={
                            "filter": "drop-shadow(0 20px 40px rgba(255, 255, 255, 0.3))",
                            "transform": "perspective(1000px) rotateX(5deg)",
                            "transition": "transform 0.3s ease",
                            "object_fit": "contain",
                            "_hover": {
                                "transform": "perspective(1000px) rotateX(0deg) scale(1.05)"
                            }
                        }
                    ),
                    rx.text(
                        "Your Agent for Surveys",
                        size="5",
                        color="#A0A0A0",
                        font_weight="400"
                    ),
                    rx.text(
                        "Transform Google Forms into AI-powered voice campaigns",
                        size="3",
                        color="#A0A0A0",
                        text_align="center",
                        max_width="400px",
                        margin_top="4"
                    ),
                    spacing="4",
                    align="center",
                    justify="center"
                ),
                width="50%",
                height="100vh",
                background="#000000",
                display="flex",
                align_items="center",
                justify_content="center"
            ),

            # Right side - Login Form
            rx.box(
                rx.vstack(
                    rx.heading(
                        "Welcome Back",
                        size="8",
                        color="#000000",
                        font_weight="600",
                        margin_bottom="2"
                    ),
                    rx.text(
                        "Sign in to continue to your dashboard",
                        size="3",
                        color="#A0A0A0",
                        margin_bottom="6"
                    ),

                    # Email/Password Form
                    rx.vstack(
                        rx.input(
                            placeholder="Email address",
                            value=AuthState.email,
                            on_change=AuthState.set_email,
                            size="3",
                            width="100%",
                            type="email",
                            color="#1A1A1A",
                            style={
                                "border_radius": "12px",
                                "padding": "16px",
                                "border": "1px solid #A0A0A0",
                                "background": "#FFFFFF",
                                "color": "#1A1A1A",
                                "_placeholder": {"color": "#666666"}
                            }
                        ),
                        rx.input(
                            placeholder="Password",
                            value=AuthState.password,
                            on_change=AuthState.set_password,
                            type="password",
                            size="3",
                            width="100%",
                            color="#1A1A1A",
                            style={
                                "border_radius": "12px",
                                "padding": "16px",
                                "border": "1px solid #A0A0A0",
                                "background": "#FFFFFF",
                                "color": "#1A1A1A",
                                "_placeholder": {"color": "#666666"}
                            }
                        ),
                        rx.button(
                            rx.cond(
                                AuthState.loading,
                                rx.spinner(size="2", color="white"),
                                rx.text("Sign In")
                            ),
                            on_click=AuthState.login_with_supabase,
                            width="100%",
                            size="3",
                            disabled=AuthState.loading,
                            style={
                                "background": "#000000",
                                "color": "#FFFFFF",
                                "border_radius": "12px",
                                "padding": "16px",
                                "font_weight": "500",
                                "cursor": "pointer",
                                "_hover": {"background": "#A0A0A0"},
                                "_disabled": {"opacity": "0.5", "cursor": "not-allowed"}
                            }
                        ),
                        spacing="4",
                        width="100%"
                    ),

                    # Sign up link
                    rx.hstack(
                        rx.text("Don't have an account?", size="2", color="#A0A0A0"),
                        rx.link(
                            rx.text("Sign up", size="2", color="#000000", font_weight="500"),
                            href="/signup"
                        ),
                        spacing="2",
                        margin_top="6"
                    ),

                    # Error message
                    rx.cond(
                        AuthState.error_message,
                        rx.box(
                            rx.hstack(
                                rx.icon(tag="circle-alert", size=16, color="red"),
                                rx.text(AuthState.error_message, size="2", color="red"),
                                spacing="2",
                                align="center"
                            ),
                            padding="12px",
                            background="rgba(255,0,0,0.1)",
                            border_radius="8px",
                            border="1px solid rgba(255,0,0,0.3)",
                            margin_top="4",
                            width="100%"
                        ),
                        rx.box()
                    ),

                    spacing="4",
                    width="100%",
                    max_width="400px"
                ),
                width="50%",
                height="100vh",
                background="#F5F5F5",
                display="flex",
                align_items="center",
                justify_content="center",
                padding="40px"
            ),

            spacing="0",
            width="100%"
        ),
        width="100%",
        height="100vh",
        overflow="hidden"
    )
