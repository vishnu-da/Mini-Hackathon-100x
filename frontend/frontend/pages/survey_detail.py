"""Survey detail page - Configure and launch survey."""
import reflex as rx
from frontend.state.survey_detail_state import SurveyDetailState


def sidebar() -> rx.Component:
    """Left sidebar navigation."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.image(src="/logo.png", width="32px", height="32px", alt="RESO"),
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


def survey_detail_page() -> rx.Component:
    """Survey detail/configuration page."""
    return rx.box(
        # Sidebar
        sidebar(),

        # Main content area
        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.vstack(
                        rx.heading(
                            rx.cond(
                                SurveyDetailState.survey,
                                SurveyDetailState.survey.json_questionnaire.get("title", "Untitled Survey"),
                                "Loading..."
                            ),
                            size="9",
                            color="#FFFFFF",
                            font_weight="600"
                        ),
                        rx.cond(
                            SurveyDetailState.survey,
                            rx.text(
                                SurveyDetailState.survey.survey_id,
                                size="2",
                                color="#A0A0A0"
                            ),
                            rx.text(
                                "Loading...",
                                size="2",
                                color="#A0A0A0"
                            )
                        ),
                        spacing="2",
                        align="start"
                    ),
                    rx.spacer(),
                    rx.badge(
                        rx.cond(
                            SurveyDetailState.survey,
                            SurveyDetailState.survey.status.capitalize(),
                            "..."
                        ),
                        color_scheme="gray",
                        size="3"
                    ),
                    width="100%",
                    align="center",
                    margin_bottom="6"
                ),

                # CSV Upload Section
                rx.box(
                    rx.vstack(
                        rx.heading("Upload Contacts", size="6", color="#000000", margin_bottom="3"),
                        rx.text(
                            "Upload a CSV file with contact information. Required columns: name, phone_number",
                            size="3",
                            color="#4f5253",
                            margin_bottom="4"
                        ),

                        # Upload area
                        rx.upload(
                            rx.vstack(
                                rx.button(
                                    rx.hstack(
                                        rx.icon(tag="upload", size=20, color="white"),
                                        rx.text("Choose CSV File"),
                                        spacing="2",
                                        align="center"
                                    ),
                                    size="3",
                                    style={
                                        "background": "#000000",
                                        "color": "#FFFFFF",
                                        "border_radius": "12px",
                                        "padding": "12px 24px",
                                        "_hover": {"background": "#A0A0A0"}
                                    }
                                ),
                                rx.text(
                                    "or drag and drop CSV file here",
                                    size="2",
                                    color="#999999"
                                ),
                                spacing="3",
                                align="center",
                                padding="40px",
                                border="2px dashed #E0E0E0",
                                border_radius="12px",
                                width="100%",
                                _hover={"border_color": "#A0A0A0"}
                            ),
                            id="csv_upload",
                            accept={".csv": ["text/csv"]},
                            max_files=1,
                            on_drop=SurveyDetailState.handle_upload
                        ),

                        # Uploaded file info
                        rx.cond(
                            SurveyDetailState.csv_uploaded,
                            rx.box(
                                rx.hstack(
                                    rx.icon(tag="file-text", size=20, color="green"),
                                    rx.vstack(
                                        rx.text(
                                            SurveyDetailState.csv_filename,
                                            size="3",
                                            color="#000000",
                                            font_weight="500"
                                        ),
                                        rx.text(
                                            f"{SurveyDetailState.contacts_count} contacts loaded",
                                            size="2",
                                            color="#4f5253"
                                        ),
                                        spacing="1",
                                        align="start"
                                    ),
                                    rx.spacer(),
                                    rx.button(
                                        rx.icon(tag="x", size=16),
                                        on_click=SurveyDetailState.clear_csv,
                                        size="1",
                                        variant="ghost",
                                        color_scheme="gray"
                                    ),
                                    spacing="3",
                                    align="center",
                                    width="100%"
                                ),
                                background="#F0FFF0",
                                border="1px solid #90EE90",
                                border_radius="8px",
                                padding="12px",
                                margin_top="3"
                            ),
                            rx.box()
                        ),

                        spacing="4",
                        width="100%"
                    ),
                    background="#FFFFFF",
                    border_radius="12px",
                    padding="24px",
                    box_shadow="0 4px 8px rgba(0,0,0,0.1)",
                    width="100%",
                    margin_bottom="4"
                ),

                # Voice Agent Configuration Section
                rx.box(
                    rx.vstack(
                        rx.heading("Voice Agent Configuration", size="6", color="#000000", margin_bottom="3"),

                        # Voice Tone
                        rx.vstack(
                            rx.text("Voice Tone", size="3", color="#000000", font_weight="500"),
                            rx.select(
                                ["friendly", "professional", "casual"],
                                value=SurveyDetailState.voice_tone,
                                on_change=SurveyDetailState.set_voice_tone,
                                size="3",
                                style={
                                    "border_radius": "8px",
                                    "border": "1px solid #E0E0E0",
                                    "width": "100%"
                                }
                            ),
                            spacing="2",
                            width="100%"
                        ),

                        # Voice Model
                        rx.vstack(
                            rx.text("Voice Model", size="3", color="#000000", font_weight="500"),
                            rx.select(
                                ["astra", "luna", "nova"],
                                value=SurveyDetailState.voice_model,
                                on_change=SurveyDetailState.set_voice_model,
                                size="3",
                                style={
                                    "border_radius": "8px",
                                    "border": "1px solid #E0E0E0",
                                    "width": "100%"
                                }
                            ),
                            spacing="2",
                            width="100%"
                        ),

                        # Custom Instructions
                        rx.vstack(
                            rx.text("Custom Instructions (Optional)", size="3", color="#000000", font_weight="500"),
                            rx.text_area(
                                placeholder="Add custom instructions for the voice agent...",
                                value=SurveyDetailState.custom_instructions,
                                on_change=SurveyDetailState.set_custom_instructions,
                                rows="4",
                                style={
                                    "border_radius": "8px",
                                    "border": "1px solid #E0E0E0",
                                    "padding": "12px",
                                    "width": "100%",
                                    "_placeholder": {"color": "#4f5253"}
                                }
                            ),
                            spacing="2",
                            width="100%"
                        ),

                        # Max Call Duration
                        rx.vstack(
                            rx.text("Max Call Duration (minutes)", size="3", color="#000000", font_weight="500"),
                            rx.hstack(
                                rx.slider(
                                    default_value=[SurveyDetailState.max_duration],
                                    on_value_commit=lambda value: SurveyDetailState.set_max_duration(value[0]),
                                    min=1,
                                    max=30,
                                    step=1,
                                    width="300px"
                                ),
                                rx.text(
                                    f"{SurveyDetailState.max_duration} min",
                                    size="3",
                                    color="#000000",
                                    font_weight="500"
                                ),
                                spacing="4",
                                align="center"
                            ),
                            spacing="2",
                            width="100%"
                        ),

                        spacing="5",
                        width="100%"
                    ),
                    background="#FFFFFF",
                    border_radius="12px",
                    padding="24px",
                    box_shadow="0 4px 8px rgba(0,0,0,0.1)",
                    width="100%",
                    margin_bottom="4"
                ),

                # Error/Success messages
                rx.cond(
                    SurveyDetailState.error_message,
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="circle-alert", size=16, color="red"),
                            rx.text(SurveyDetailState.error_message, size="3", color="red"),
                            spacing="2",
                            align="center"
                        ),
                        padding="12px",
                        background="rgba(255,0,0,0.1)",
                        border_radius="8px",
                        border="1px solid rgba(255,0,0,0.3)",
                        width="100%",
                        margin_bottom="4"
                    ),
                    rx.box()
                ),

                rx.cond(
                    SurveyDetailState.success_message,
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="circle-check", size=16, color="green"),
                            rx.text(SurveyDetailState.success_message, size="3", color="green"),
                            spacing="2",
                            align="center"
                        ),
                        padding="12px",
                        background="rgba(0,255,0,0.1)",
                        border_radius="8px",
                        border="1px solid rgba(0,255,0,0.3)",
                        width="100%",
                        margin_bottom="4"
                    ),
                    rx.box()
                ),

                # Action Buttons
                rx.hstack(
                    rx.link(
                        rx.button(
                            "Back to Dashboard",
                            size="3",
                            variant="outline",
                            style={
                                "border": "1px solid #A0A0A0",
                                "color": "#FFFFFF",
                                "border_radius": "12px",
                                "padding": "12px 24px",
                                "_hover": {"background": "#FFFFFF", "color": "#000000"}
                            }
                        ),
                        href="/dashboard"
                    ),
                    rx.spacer(),
                    rx.button(
                        "Save Configuration",
                        on_click=SurveyDetailState.save_configuration,
                        size="3",
                        style={
                            "background": "#A0A0A0",
                            "color": "#FFFFFF",
                            "border_radius": "12px",
                            "padding": "12px 24px",
                            "_hover": {"background": "#000000"}
                        }
                    ),
                    rx.button(
                        rx.cond(
                            SurveyDetailState.loading,
                            rx.spinner(size="2", color="white"),
                            rx.text("Launch Campaign")
                        ),
                        on_click=SurveyDetailState.launch_campaign,
                        disabled=SurveyDetailState.loading | ~SurveyDetailState.csv_uploaded,
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
                    width="100%",
                    align="center"
                ),

                spacing="6",
                width="100%",
                max_width="800px",
                padding="40px"
            ),
            margin_left="240px",
            min_height="100vh",
            background="#000000"
        ),

        background="#000000",
        min_height="100vh",
        on_mount=SurveyDetailState.load_survey
    )
