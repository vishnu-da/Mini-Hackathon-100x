"""Dashboard page - Apple iOS minimalist design."""
import reflex as rx
from frontend.state.survey_state import SurveyState


def kpi_card(label: str, value: str) -> rx.Component:
    """Modern KPI card with black/white/grey theme."""
    return rx.box(
        rx.vstack(
            rx.text(label, size="2", color="#A0A0A0", font_weight="500"),
            rx.heading(value, size="8", color="#000000", font_weight="600"),
            spacing="2",
            align="start",
            width="100%"
        ),
        background="#FFFFFF",
        border_radius="12px",
        padding="24px",
        box_shadow="0 4px 8px rgba(0,0,0,0.1)",
        min_width="200px",
        flex="1"
    )


def survey_row(survey) -> rx.Component:
    """Modern survey table row."""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text(
                    rx.cond(
                        survey.json_questionnaire.title,
                        survey.json_questionnaire.title,
                        "Untitled Survey"
                    ),
                    size="4",
                    color="#000000",
                    font_weight="500"
                ),
                rx.text(survey.created_at, size="2", color="#A0A0A0"),
                spacing="1",
                align="start",
                flex="1"
            ),
            rx.badge(
                survey.status.capitalize(),
                color_scheme=rx.cond(survey.status == "active", "green", "gray"),
                size="2"
            ),
            rx.hstack(
                rx.link(
                    rx.button(
                        "View",
                        size="2",
                        style={
                            "background": "#A0A0A0",
                            "color": "#FFFFFF",
                            "border_radius": "8px",
                            "_hover": {"background": "#bbbbbb"}
                        }
                    ),
                    href=f"/survey/{survey.survey_id}"
                ),
                rx.link(
                    rx.button(
                        "Responses",
                        size="2",
                        style={
                            "background": "#bbbbbb",
                            "color": "#FFFFFF",
                            "border_radius": "8px",
                            "_hover": {"background": "#A0A0A0"}
                        }
                    ),
                    href=f"/survey/{survey.survey_id}/responses"
                ),
                spacing="3"
            ),
            spacing="4",
            align="center",
            width="100%",
            justify="between"
        ),
        background="#FFFFFF",
        border_radius="12px",
        padding="20px",
        margin_bottom="12px",
        box_shadow="0 2px 4px rgba(0,0,0,0.05)",
        _hover={"box_shadow": "0 4px 12px rgba(0,0,0,0.1)"},
        transition="all 0.2s ease"
    )


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
                        rx.text("Dashboard", size="3", color="#FFFFFF"),
                        padding="12px 16px",
                        border_radius="8px",
                        background="#A0A0A0",
                        _hover={"background": "#FFFFFF", "color": "#000000"},
                        width="100%"
                    ),
                    href="/dashboard"
                ),
                rx.link(
                    rx.box(
                        rx.text("Add Survey", size="3", color="#A0A0A0"),
                        padding="12px 16px",
                        border_radius="8px",
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


def dashboard_page() -> rx.Component:
    """Main dashboard with Apple iOS aesthetic."""
    return rx.box(
        # Sidebar
        sidebar(),

        # Main content area
        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.heading("My Surveys", size="9", color="#FFFFFF", font_weight="600"),
                    rx.spacer(),
                    rx.link(
                        rx.button(
                            "+ New Survey",
                            size="3",
                            style={
                                "background": "#FFFFFF",
                                "color": "#000000",
                                "border_radius": "12px",
                                "padding": "12px 24px",
                                "font_weight": "500",
                                "_hover": {"background": "#A0A0A0", "color": "#FFFFFF"}
                            }
                        ),
                        href="/survey/new"
                    ),
                    width="100%",
                    align="center",
                    margin_bottom="6"
                ),

                # KPI Cards
                rx.hstack(
                    kpi_card("Active Surveys", SurveyState.active_surveys.to_string()),
                    kpi_card("Total Responses", "0"),
                    kpi_card("Time Saved", "0h 0m"),
                    kpi_card("Avg. Response Length", "0 words"),
                    spacing="4",
                    width="100%",
                    margin_bottom="6"
                ),

                # Surveys Section
                rx.box(
                    rx.heading("Surveys", size="6", color="#FFFFFF", margin_bottom="4"),
                    rx.cond(
                        SurveyState.loading,
                        rx.center(
                            rx.spinner(size="3", color="#FFFFFF"),
                            padding="8"
                        ),
                        rx.cond(
                            SurveyState.has_surveys,
                            rx.vstack(
                                rx.foreach(SurveyState.surveys, survey_row),
                                spacing="0",
                                width="100%"
                            ),
                            rx.box(
                                rx.vstack(
                                    rx.icon(tag="inbox", size=48, color="#A0A0A0"),
                                    rx.text("No surveys yet", size="4", color="#A0A0A0"),
                                    rx.link(
                                        rx.button(
                                            "Create Your First Survey",
                                            size="3",
                                            style={
                                                "background": "#FFFFFF",
                                                "color": "#000000",
                                                "border_radius": "12px",
                                                "padding": "12px 24px",
                                                "_hover": {"background": "#A0A0A0", "color": "#FFFFFF"}
                                            }
                                        ),
                                        href="/survey/new"
                                    ),
                                    spacing="4",
                                    align="center"
                                ),
                                background="#FFFFFF",
                                border_radius="12px",
                                padding="60px",
                                text_align="center"
                            )
                        )
                    ),
                    width="100%"
                ),

                spacing="6",
                width="100%",
                padding="40px"
            ),
            margin_left="240px",
            min_height="100vh",
            background="#000000"
        ),

        background="#000000",
        min_height="100vh",
        on_mount=SurveyState.load_surveys
    )
