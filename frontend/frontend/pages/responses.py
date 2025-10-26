"""Survey responses page - displays call logs."""
import reflex as rx
from frontend.state.responses_state import ResponsesState
from frontend.pages.dashboard import sidebar


def call_log_row(log) -> rx.Component:
    """Table row for a single call log."""
    return rx.table.row(
        rx.table.cell(
            rx.text(
                rx.cond(
                    log.get("participant_name"),
                    log["participant_name"],
                    "Unknown"
                ),
                size="2",
                color="#4A4A4A",
                font_weight="500"
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(
                    log.get("call_timestamp"),
                    log["call_timestamp"],
                    "N/A"
                ),
                size="2",
                color="#4A4A4A"
            )
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(
                    log.get("status"),
                    log["status"],
                    "unknown"
                ),
                color_scheme=rx.match(
                    log.get("status", "unknown"),
                    ("completed", "green"),
                    ("failed", "red"),
                    ("in_progress", "blue"),
                    "gray"
                ),
                size="2"
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(
                    log.get("call_duration"),
                    f"{log['call_duration']}s",
                    "N/A"
                ),
                size="2",
                color="#4A4A4A"
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(
                    log.get("consent"),
                    "Yes",
                    "No"
                ),
                size="2",
                color="#4A4A4A"
            )
        ),
        rx.table.cell(
            rx.cond(
                log.get("mapped_responses"),
                rx.text(
                    rx.cond(
                        log["mapped_responses"],
                        str(log["mapped_responses"]),
                        "-"
                    ),
                    size="1",
                    color="#4A4A4A",
                    white_space="pre-wrap"
                ),
                rx.text("-", size="2", color="#A0A0A0")
            )
        ),
        rx.table.cell(
            rx.cond(
                log.get("error_message"),
                rx.text(log["error_message"], size="1", color="#4A4A4A"),
                rx.text("-", size="2", color="#A0A0A0")
            )
        ),
    )


def responses_page() -> rx.Component:
    """Survey responses page with call logs table."""
    return rx.box(
        sidebar(),

        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.vstack(
                        rx.heading(
                            rx.cond(
                                ResponsesState.survey,
                                ResponsesState.survey.json_questionnaire.title,
                                "Loading..."
                            ),
                            size="9",
                            color="#FFFFFF",
                            font_weight="600"
                        ),
                        rx.text("Survey Responses", size="3", color="#A0A0A0"),
                        spacing="1",
                        align="start"
                    ),
                    rx.spacer(),
                    rx.button(
                        "Download CSV",
                        size="3",
                        on_click=ResponsesState.download_csv,
                        style={
                            "background": "#FFFFFF",
                            "color": "#000000",
                            "border_radius": "12px",
                            "padding": "12px 24px",
                            "font_weight": "500",
                            "_hover": {"background": "#A0A0A0", "color": "#FFFFFF"}
                        }
                    ),
                    width="100%",
                    align="center",
                    margin_bottom="6"
                ),

                # Error/Success messages
                rx.cond(
                    ResponsesState.error_message != "",
                    rx.callout(
                        ResponsesState.error_message,
                        icon="circle-alert",
                        color_scheme="red",
                        role="alert",
                        margin_bottom="4"
                    )
                ),
                rx.cond(
                    ResponsesState.success_message != "",
                    rx.callout(
                        ResponsesState.success_message,
                        icon="circle-check",
                        color_scheme="green",
                        margin_bottom="4"
                    )
                ),

                # Call Logs Table
                rx.box(
                    rx.cond(
                        ResponsesState.loading,
                        rx.center(
                            rx.spinner(size="3", color="#FFFFFF"),
                            padding="8"
                        ),
                        rx.cond(
                            ResponsesState.call_logs.length() > 0,
                            rx.box(
                                rx.table.root(
                                    rx.table.header(
                                        rx.table.row(
                                            rx.table.column_header_cell("Participant", style={"color": "#000000"}),
                                            rx.table.column_header_cell("Timestamp", style={"color": "#000000"}),
                                            rx.table.column_header_cell("Status", style={"color": "#000000"}),
                                            rx.table.column_header_cell("Duration", style={"color": "#000000"}),
                                            rx.table.column_header_cell("Consent", style={"color": "#000000"}),
                                            rx.table.column_header_cell("Responses", style={"color": "#000000"}),
                                            rx.table.column_header_cell("Error", style={"color": "#000000"}),
                                        )
                                    ),
                                    rx.table.body(
                                        rx.foreach(ResponsesState.call_logs, call_log_row)
                                    ),
                                    variant="surface",
                                    size="3",
                                    width="100%"
                                ),
                                background="#FFFFFF",
                                border_radius="12px",
                                padding="24px",
                                box_shadow="0 4px 8px rgba(0,0,0,0.1)",
                                overflow_x="auto"
                            ),
                            rx.box(
                                rx.vstack(
                                    rx.icon(tag="inbox", size=48, color="#A0A0A0"),
                                    rx.text("No responses yet", size="4", color="#A0A0A0"),
                                    rx.text(
                                        "Launch a campaign to start collecting responses",
                                        size="2",
                                        color="#A0A0A0"
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
        on_mount=ResponsesState.load_responses
    )
