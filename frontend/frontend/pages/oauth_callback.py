"""OAuth callback pages for Google and Microsoft."""
import reflex as rx


def oauth_success_page() -> rx.Component:
    """OAuth connection success page."""
    return rx.box(
        rx.vstack(
            # Success Icon
            rx.box(
                rx.icon(
                    tag="circle-check",
                    size=64,
                    color="green"
                ),
                padding="20px"
            ),

            # Success Message
            rx.heading(
                "Connection Successful!",
                size="8",
                color="#000000",
                font_weight="600",
                margin_bottom="4"
            ),

            rx.text(
                "Your account has been connected successfully.",
                size="4",
                color="#4f5253",
                text_align="center",
                margin_bottom="8"
            ),

            # Instructions
            rx.box(
                rx.vstack(
                    rx.text(
                        "You can now:",
                        size="3",
                        color="#000000",
                        font_weight="500"
                    ),
                    rx.vstack(
                        rx.text("• Close this window", size="3", color="#4f5253"),
                        rx.text("• Return to the survey creation page", size="3", color="#4f5253"),
                        rx.text("• Try fetching your form again", size="3", color="#4f5253"),
                        spacing="2",
                        align="start"
                    ),
                    spacing="3",
                    align="start"
                ),
                background="#F5F5F5",
                border_radius="12px",
                padding="20px",
                max_width="400px"
            ),

            # Button to go back
            rx.link(
                rx.button(
                    "Go to Dashboard",
                    size="3",
                    style={
                        "background": "#000000",
                        "color": "#FFFFFF",
                        "border_radius": "12px",
                        "padding": "12px 32px",
                        "_hover": {"background": "#A0A0A0"},
                        "margin_top": "20px"
                    }
                ),
                href="/dashboard"
            ),

            spacing="6",
            align="center",
            justify="center",
            padding="60px 40px"
        ),
        width="100%",
        min_height="100vh",
        background="#FFFFFF",
        display="flex",
        align_items="center",
        justify_content="center"
    )


def oauth_error_page() -> rx.Component:
    """OAuth connection error page."""
    return rx.box(
        rx.vstack(
            # Error Icon
            rx.box(
                rx.icon(
                    tag="circle-alert",
                    size=64,
                    color="red"
                ),
                padding="20px"
            ),

            # Error Message
            rx.heading(
                "Connection Failed",
                size="8",
                color="#000000",
                font_weight="600",
                margin_bottom="4"
            ),

            rx.text(
                "There was an error connecting your account.",
                size="4",
                color="#4f5253",
                text_align="center",
                margin_bottom="8"
            ),

            # Instructions
            rx.box(
                rx.vstack(
                    rx.text(
                        "What to do next:",
                        size="3",
                        color="#000000",
                        font_weight="500"
                    ),
                    rx.vstack(
                        rx.text("• Try connecting again", size="3", color="#4f5253"),
                        rx.text("• Make sure you grant all required permissions", size="3", color="#4f5253"),
                        rx.text("• Contact support if the problem persists", size="3", color="#4f5253"),
                        spacing="2",
                        align="start"
                    ),
                    spacing="3",
                    align="start"
                ),
                background="#FFF5F5",
                border_radius="12px",
                padding="20px",
                max_width="400px",
                border="1px solid rgba(255,0,0,0.2)"
            ),

            # Buttons
            rx.hstack(
                rx.link(
                    rx.button(
                        "Try Again",
                        size="3",
                        style={
                            "background": "#000000",
                            "color": "#FFFFFF",
                            "border_radius": "12px",
                            "padding": "12px 32px",
                            "_hover": {"background": "#A0A0A0"}
                        }
                    ),
                    href="/survey/new"
                ),
                rx.link(
                    rx.button(
                        "Go to Dashboard",
                        size="3",
                        style={
                            "background": "#FFFFFF",
                            "color": "#000000",
                            "border": "1px solid #A0A0A0",
                            "border_radius": "12px",
                            "padding": "12px 32px",
                            "_hover": {"background": "#F5F5F5"}
                        }
                    ),
                    href="/dashboard"
                ),
                spacing="4",
                margin_top="20px"
            ),

            spacing="6",
            align="center",
            justify="center",
            padding="60px 40px"
        ),
        width="100%",
        min_height="100vh",
        background="#FFFFFF",
        display="flex",
        align_items="center",
        justify_content="center"
    )
