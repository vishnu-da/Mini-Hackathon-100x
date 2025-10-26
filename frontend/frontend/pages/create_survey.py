"""Create survey page - Apple iOS minimalist design."""
import reflex as rx
from frontend.state.survey_state import SurveyState


def sidebar() -> rx.Component:
    """Left sidebar navigation."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.image(src="/logo2.png", width="32px", height="32px", alt="RESO"),
                rx.heading("RESO", size="5", color="#FFFFFF"),
                spacing="3",
                align="center",
                margin_bottom="8"
            ),
            rx.vstack(
                rx.link(
                    rx.box(
                        rx.text("Dashboard", size="3", color="#A0A0A0"),
                        padding="12px 16px",
                        border_radius="8px",
                        _hover={"background": "#FFFFFF", "color": "#000000"},
                        width="100%"
                    ),
                    href="/dashboard"
                ),
                rx.link(
                    rx.box(
                        rx.text("Add Survey", size="3", color="#FFFFFF"),
                        padding="12px 16px",
                        border_radius="8px",
                        background="#A0A0A0",
                        _hover={"background": "#FFFFFF", "color": "#000000"},
                        width="100%"
                    ),
                    href="/survey/new"
                ),
                spacing="2",
                width="100%"
            ),
            spacing="6",
            align="start",
            width="100%"
        ),
        width="240px",
        background="#000000",
        padding="24px 16px",
        border_right="1px solid #A0A0A0",
        height="100vh",
        position="fixed",
        left="0",
        top="0"
    )


def create_survey_page() -> rx.Component:
    """Create survey page with black/white minimalist design."""
    return rx.box(
        # Sidebar
        sidebar(),

        # Main content area
        rx.box(
            rx.vstack(
                # Header
                rx.heading("Create New Survey", size="9", color="#FFFFFF", font_weight="600", margin_bottom="6"),

                # OAuth Connection Status Card
                rx.box(
                    rx.vstack(
                        rx.heading("Step 1: Connect Google Account", size="6", color="#000000", margin_bottom="3"),
                        rx.text(
                            "Connect your Google account to import Google Forms",
                            size="3",
                            color="#666666",
                            margin_bottom="4"
                        ),

                        # Google Connection Status
                        rx.hstack(
                            rx.box(
                                rx.hstack(
                                    # Use rx.cond to conditionally render icon
                                    rx.cond(
                                        SurveyState.google_connected,
                                        rx.icon(tag="circle-check", size=20, color="green"),
                                        rx.icon(tag="circle", size=20, color="#A0A0A0")
                                    ),
                                    rx.text(
                                        "Google Forms",
                                        size="3",
                                        color="#000000",
                                        font_weight="500"
                                    ),
                                    spacing="2",
                                    align="center"
                                ),
                                flex="1"
                            ),
                            rx.cond(
                                SurveyState.google_connected,
                                rx.text("Connected", size="2", color="green", font_weight="500"),
                                rx.button(
                                    "Connect Google",
                                    on_click=SurveyState.open_oauth_dialog,
                                    size="2",
                                    style={
                                        "background": "#4285F4",
                                        "color": "#FFFFFF",
                                        "border_radius": "8px",
                                        "padding": "8px 16px",
                                        "_hover": {"opacity": "0.9"},
                                        "cursor": "pointer"
                                    }
                                )
                            ),
                            width="100%",
                            align="center",
                            padding="12px",
                            border_radius="8px",
                            border="1px solid #E0E0E0"
                        ),

                        spacing="3",
                        width="100%"
                    ),
                    background="#FFFFFF",
                    border_radius="12px",
                    padding="24px",
                    box_shadow="0 4px 8px rgba(0,0,0,0.1)",
                    max_width="600px",
                    width="100%",
                    margin_bottom="4",
                    on_mount=SurveyState.check_oauth_connections
                ),

                # Form card
                rx.box(
                    rx.vstack(
                        rx.heading("Step 2: Import Form", size="6", color="#000000", margin_bottom="4"),

                        # Google Form URL
                        rx.vstack(
                            rx.text("Google Form URL", size="3", color="#000000", font_weight="500"),
                            rx.input(
                                placeholder="https://docs.google.com/forms/d/...",
                                value=SurveyState.form_url,
                                on_change=SurveyState.set_form_url,
                                size="3",
                                width="100%",
                                color="#000000",
                                style={
                                    "border_radius": "12px",
                                    "padding": "12px",
                                    "border": "1px solid #A0A0A0",
                                    "background": "#FFFFFF",
                                    "color": "#000000",
                                    "_placeholder": {"color": "#4f5253"}
                                }
                            ),
                            width="100%",
                            spacing="2"
                        ),

                        # Terms and Conditions
                        rx.vstack(
                            rx.text("Terms and Conditions (Optional)", size="3", color="#000000", font_weight="500"),
                            rx.text_area(
                                placeholder="Enter consent text...",
                                value=SurveyState.terms_and_conditions,
                                on_change=SurveyState.set_terms_and_conditions,
                                width="100%",
                                rows="6",
                                color="#000000",
                                style={
                                    "border_radius": "12px",
                                    "padding": "12px",
                                    "border": "1px solid #A0A0A0",
                                    "background": "#FFFFFF",
                                    "color": "#000000",
                                    "_placeholder": {"color": "#4f5253"}
                                }
                            ),
                            width="100%",
                            spacing="2"
                        ),

                        # Buttons
                        rx.hstack(
                            rx.link(
                                rx.button(
                                    "Cancel",
                                    size="3",
                                    style={
                                        "background": "#FFFFFF",
                                        "color": "#000000",
                                        "border": "1px solid #A0A0A0",
                                        "border_radius": "12px",
                                        "padding": "12px 24px",
                                        "_hover": {"background": "#F5F5F5"}
                                    }
                                ),
                                href="/dashboard"
                            ),
                            rx.button(
                                rx.cond(
                                    SurveyState.loading,
                                    rx.spinner(size="2", color="white"),
                                    rx.text("Fetch Survey")
                                ),
                                on_click=SurveyState.create_survey,
                                disabled=SurveyState.loading,
                                size="3",
                                style={
                                    "background": "#000000",
                                    "color": "#FFFFFF",
                                    "border_radius": "12px",
                                    "padding": "12px 24px",
                                    "_hover": {"background": "#A0A0A0"},
                                    "_disabled": {"opacity": "0.5", "cursor": "not-allowed"}
                                }
                            ),
                            spacing="4",
                            margin_top="4"
                        ),

                        spacing="6",
                        width="100%"
                    ),
                    background="#FFFFFF",
                    border_radius="12px",
                    padding="32px",
                    box_shadow="0 4px 8px rgba(0,0,0,0.1)",
                    max_width="600px",
                    width="100%"
                ),

                # Error/Success messages
                rx.cond(
                    SurveyState.error_message,
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="circle-alert", size=16, color="red"),
                            rx.text(SurveyState.error_message, size="3", color="red"),
                            spacing="2",
                            align="center"
                        ),
                        padding="12px",
                        background="rgba(255,0,0,0.1)",
                        border_radius="8px",
                        border="1px solid rgba(255,0,0,0.3)",
                        max_width="600px",
                        width="100%"
                    ),
                    rx.box()
                ),

                rx.cond(
                    SurveyState.success_message,
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="circle-check", size=16, color="green"),
                            rx.text(SurveyState.success_message, size="3", color="green"),
                            spacing="2",
                            align="center"
                        ),
                        padding="12px",
                        background="rgba(0,255,0,0.1)",
                        border_radius="8px",
                        border="1px solid rgba(0,255,0,0.3)",
                        max_width="600px",
                        width="100%"
                    ),
                    rx.box()
                ),

                spacing="6",
                width="100%",
                padding="40px",
                align="center"
            ),
            margin_left="240px",
            min_height="100vh",
            background="#000000"
        ),

        # OAuth Connection Dialog
        rx.dialog.root(
            rx.dialog.content(
                rx.vstack(
                    # Header with close button
                    rx.hstack(
                        rx.heading("Connect Google Account", size="5", color="#000000"),
                        rx.dialog.close(
                            rx.icon(tag="x", size=20, color="#666666", cursor="pointer")
                        ),
                        justify="between",
                        width="100%",
                        margin_bottom="4"
                    ),

                    # Instructions
                    rx.text(
                        "Click the button below to authorize RESO to access your Google Forms.",
                        size="3",
                        color="#4f5253",
                        margin_bottom="4"
                    ),

                    # OAuth URL redirect button
                    rx.link(
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="external-link", size=16, color="white"),
                                rx.text("Go to Google Authorization"),
                                spacing="2",
                                align="center"
                            ),
                            size="3",
                            style={
                                "background": "#4285F4",
                                "color": "#FFFFFF",
                                "border_radius": "8px",
                                "padding": "12px 24px",
                                "_hover": {"opacity": "0.9"},
                                "cursor": "pointer",
                                "width": "100%"
                            }
                        ),
                        href=SurveyState.google_oauth_url,
                        is_external=False
                    ),

                    # Info text
                    rx.text(
                        "You will be redirected to Google's authorization page. After granting access, you'll be redirected back here.",
                        size="2",
                        color="#999999",
                        margin_top="4",
                        text_align="center"
                    ),

                    spacing="4",
                    width="100%"
                ),
                style={
                    "max_width": "450px",
                    "padding": "24px",
                    "border_radius": "12px"
                }
            ),
            open=SurveyState.show_oauth_dialog,
            on_open_change=SurveyState.set_show_oauth_dialog
        ),

        background="#000000",
        min_height="100vh"
    )
