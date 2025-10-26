"""Card component for consistent styling."""
import reflex as rx


def card(
    *children,
    header: str = None,
    **props
) -> rx.Component:
    """Render a styled card."""
    content = []

    if header:
        content.append(
            rx.heading(header, size="5", margin_bottom="4")
        )

    content.extend(children)

    return rx.box(
        *content,
        padding="6",
        border_radius="lg",
        border="1px solid",
        border_color="gray.200",
        bg="white",
        box_shadow="sm",
        **props
    )


def stat_card(label: str, value: str, icon: str = None) -> rx.Component:
    """Render a stat card."""
    return rx.box(
        rx.vstack(
            rx.text(label, size="2", color="gray.600"),
            rx.heading(value, size="7", color="blue.600"),
            spacing="2",
            align="start"
        ),
        padding="6",
        border_radius="lg",
        bg="blue.50",
        border="1px solid",
        border_color="blue.200"
    )
