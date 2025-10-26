"""Alert components for messages."""
import reflex as rx


def error_alert(message: str) -> rx.Component:
    """Render error alert."""
    return rx.cond(
        message != "",
        rx.box(
            rx.hstack(
                rx.icon(tag="circle-alert", color="red.600"),
                rx.text(message, color="red.800"),
                spacing="2"
            ),
            padding="4",
            border_radius="md",
            bg="red.50",
            border="1px solid",
            border_color="red.200",
            margin_bottom="4"
        ),
        rx.box()
    )


def success_alert(message: str) -> rx.Component:
    """Render success alert."""
    return rx.cond(
        message != "",
        rx.box(
            rx.hstack(
                rx.icon(tag="circle-check", color="green.600"),
                rx.text(message, color="green.800"),
                spacing="2"
            ),
            padding="4",
            border_radius="md",
            bg="green.50",
            border="1px solid",
            border_color="green.200",
            margin_bottom="4"
        ),
        rx.box()
    )


def loading_spinner() -> rx.Component:
    """Render loading spinner."""
    return rx.center(
        rx.spinner(size="3", color="blue.600"),
        padding="8"
    )
