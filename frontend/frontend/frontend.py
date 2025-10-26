"""Main Reflex app file."""
import reflex as rx
from frontend.pages.login import login_page
from frontend.pages.dashboard import dashboard_page
from frontend.pages.create_survey import create_survey_page
from frontend.pages.survey_detail import survey_detail_page
from frontend.pages.campaign import campaign_page
from frontend.pages.oauth_callback import oauth_success_page, oauth_error_page
from frontend.pages.responses import responses_page


# Create app
app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="blue"
    )
)

# Add pages
app.add_page(login_page, route="/", title="Login - RESO AI Voice Survey")
app.add_page(login_page, route="/login", title="Login - RESO AI Voice Survey")
app.add_page(dashboard_page, route="/dashboard", title="Dashboard - RESO AI Voice Survey")
app.add_page(create_survey_page, route="/survey/new", title="Create Survey - RESO")
app.add_page(survey_detail_page, route="/survey/[survey_id]", title="Survey Details - RESO")
app.add_page(responses_page, route="/survey/[survey_id]/responses", title="Survey Responses - RESO")
app.add_page(campaign_page, route="/campaign/[survey_id]", title="Launch Campaign - RESO")
app.add_page(oauth_success_page, route="/oauth/success", title="OAuth Success - RESO")
app.add_page(oauth_error_page, route="/oauth/error", title="OAuth Error - RESO")
