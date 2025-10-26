"""Campaign page."""
import reflex as rx
from frontend.state.campaign_state import CampaignState
from frontend.state.survey_state import SurveyState
from frontend.components.navbar import navbar
from frontend.components.card import card, stat_card
from frontend.components.alerts import error_alert, success_alert


def campaign_page() -> rx.Component:
    """Campaign page."""
    return rx.box(
        navbar(),
        rx.container(
            rx.vstack(
                rx.heading("Launch Campaign", size="9"),

                error_alert(CampaignState.error_message),
                success_alert(CampaignState.success_message),

                # Campaign statistics
                rx.cond(
                    CampaignState.campaign_status,
                    card(
                        rx.vstack(
                            rx.heading("Campaign Statistics", size="6"),
                            rx.hstack(
                                stat_card("Total", CampaignState.campaign_status.total_contacts.to_string()),
                                stat_card("Completed", CampaignState.campaign_status.completed_calls.to_string()),
                                stat_card("Failed", CampaignState.campaign_status.failed_calls.to_string()),
                                spacing="4",
                                wrap="wrap"
                            ),
                            rx.progress(
                                value=CampaignState.campaign_status.completion_percentage.to(int),
                                width="100%",
                                max=100
                            ),
                            spacing="4",
                            width="100%"
                        )
                    ),
                    rx.box()
                ),

                # Phone info
                rx.cond(
                    CampaignState.phone_info,
                    rx.box(
                        rx.vstack(
                            rx.heading("Your Phone Number", size="5"),
                            rx.text(CampaignState.phone_info.phone_number),
                            rx.text(CampaignState.phone_info.status, color="gray.600"),
                            spacing="2",
                            width="100%"
                        ),
                        padding="6",
                        border_radius="lg",
                        border="1px solid",
                        border_color="green.200",
                        bg="green.50",
                        box_shadow="sm"
                    ),
                    rx.box()
                ),

                # Launch controls
                card(
                    rx.vstack(
                        rx.heading("Launch Campaign", size="6"),
                        rx.text("Click to start calling all contacts"),
                        rx.hstack(
                            rx.button(
                                "Test (1 Contact)",
                                size="3",
                                color_scheme="orange",
                                loading=CampaignState.launching
                            ),
                            rx.button(
                                "Launch Full Campaign",
                                size="3",
                                color_scheme="green",
                                loading=CampaignState.launching
                            ),
                            spacing="4"
                        ),
                        spacing="4",
                        width="100%"
                    )
                ),

                rx.link(
                    rx.button("Back to Dashboard", size="2", variant="outline"),
                    href="/dashboard"
                ),

                spacing="6",
                width="100%",
                padding_y="8"
            ),
            max_width="1000px"
        ),
        bg="gray.50",
        min_height="100vh"
    )
