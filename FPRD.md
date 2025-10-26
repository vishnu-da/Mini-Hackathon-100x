# RESO Frontend PRD - AI Agent for Surveys
**Version:** 1.0  
**Framework:** Reflex (Python)  
**Target:** 8-hour MVP build with Claude Sonnet 4.5  
**Backend:** Existing FastAPI (see PRD2.md for API reference)

---

## Executive Summary

**Product:** RESO is a web application that converts Google Forms into AI-powered voice survey campaigns. This frontend enables researchers, marketers, and agencies to import forms, upload contacts, launch campaigns, and track metrics through a professional, minimalist interface.

**Business Goal:** Acquire B2B clients (e.g., market research firms in New Zealand) by providing low-cost, high-accuracy survey automation that saves time and improves response quality vs. traditional forms.

**Success Metrics:**
- Average Response Length (words per call)
- Time Saved (total call duration + 20% efficiency gain)
- Total Responses (count across all surveys)

**Design Philosophy:** Apple iOS-inspired minimalism—black/white/grey color scheme, rounded corners (12px), clean typography, no emojis, trustworthy aesthetic.

---

## Design System

### Color Palette
COLORS = {
"background": "#000000", # Pure black
"surface": "#FFFFFF", # White cards/inputs
"text_primary": "#FFFFFF", # White text on black
"text_secondary": "#A0A0A0", # Grey accents
"button_default": "#A0A0A0", # Grey buttons
"button_hover": "#FFFFFF", # White on hover
}

text

### Component Styles (Reflex Style Dicts)
Reusable button style
button_style = {
"border_radius": "12px",
"background": "#A0A0A0",
"color": "#FFFFFF",
"padding": "12px 24px",
"cursor": "pointer",
"_hover": {"background": "#FFFFFF", "color": "#000000"},
"border": "none",
"font_weight": "500",
}

Card container style
card_style = {
"background": "#FFFFFF",
"border_radius": "12px",
"padding": "24px",
"box_shadow": "0 4px 8px rgba(0,0,0,0.1)",
"color": "#000000",
}

Top navigation bar
nav_style = {
"height": "40px",
"background": "#000000",
"color": "#FFFFFF",
"display": "flex",
"justify_content": "space_between",
"align_items": "center",
"padding": "0 24px",
"border_bottom": "1px solid #A0A0A0",
}

Sidebar menu
sidebar_style = {
"width": "240px",
"background": "#000000",
"color": "#FFFFFF",
"padding": "24px 16px",
"border_right": "1px solid #A0A0A0",
}

text

### Typography
- **Font Family:** system-ui, -apple-system, "Segoe UI"
- **Headings:** 24px (h2), 18px (h3), medium weight
- **Body:** 14px, regular weight
- **Buttons/Labels:** 14px, medium weight

---

## User Personas

**Primary: B2B Agency Admin**
- Age: 30-45, manages survey campaigns for clients
- Needs: Quick setup, scalable contact management, clear ROI metrics
- Pain: Manual calls are expensive and slow

**Secondary: Individual Researcher/Student**
- Age: 20-35, conducting thesis/public opinion polls
- Needs: Simple form import, one-click launch, quality responses
- Pain: Low Google Forms participation rates

---

## Core Features & User Flows

### 1. Authentication & Landing Page

**Layout:**
- **Top Nav (Fixed):** 40px height, black bg. Left: Logo (pear icon from image.jpg) + text "RESO - Your Agent for Surveys". Right: Profile dropdown (appears after login) with "Account Settings" / "Logout".
- **Body (Pre-Login):** Split 50/50. Left: B&W abstract image (tech/survey-themed placeholder). Right: Login/signup form centered.

**Components:**
- Email/password text inputs (rounded, white bg)
- "Login" button (primary style)
- "Sign Up" link below
- "Connect with Google" OAuth button (optional, secondary style)

**Flow:**
1. Visitor lands → sees split layout
2. Enters credentials → submits to backend auth endpoint
3. Success → redirect to /dashboard with session token
4. Profile dropdown (post-login) → settings modal or logout

**Acceptance Criteria:**
- [ ] Login form validates email format before submit
- [ ] Error toast displays on invalid credentials: "Invalid email or password"
- [ ] Successful login redirects to dashboard within 1 second
- [ ] Profile dropdown only visible when authenticated
- [ ] Logout clears session and returns to landing page

---

### 2. Dashboard (Home)

**Layout:**
- **Left Sidebar (Fixed):** 240px width. Menu items: Dashboard, Add Survey, Surveys, Settings. Active item highlighted (grey bg).
- **Main Content:** Top: 4 KPI cards in horizontal row. Bottom: Surveys table.

**KPI Cards (Metrics):**
1. Active Surveys (count)
2. Total Responses (sum across all surveys)
3. Time Saved (formatted as "X hours Y mins")
4. Avg. Response Length (words/chars)

**Surveys Table Columns:**
- Survey Name (clickable)
- Accepting Responses (Yes/No status)
- Launch Date (formatted date)
- Responses (count)

**Flow:**
1. Login success → auto-load dashboard
2. Fetch metrics and survey list from backend on mount
3. Click survey name → navigate to /surveys/{id} detail view
4. Empty state: "No surveys yet. Add your first survey!" with link to /add_survey

**Acceptance Criteria:**
- [ ] All 4 KPI cards display numerical values (0 if empty)
- [ ] Time Saved shows "0h 0m" format if no data
- [ ] Table rows are clickable and navigate correctly
- [ ] Empty state shows when no surveys exist
- [ ] Sidebar active item highlights current page

---

### 3. Add Survey

**Layout:**
- Sidebar + main content area with step-by-step form

**Sections:**
1. **Connect Google Account** (if not connected)
   - Button: "Connect Google" → triggers OAuth flow
   - After connection, show checkmark + email

2. **Import Form**
   - Text input: "Paste Google Forms edit link"
   - Button: "Fetch Form" → loads form structure
   - Validation: Must contain "docs.google.com/forms"

3. **Preview Questions** (after fetch)
   - Expandable accordion showing form questions
   - Display question text and type (text/multiple choice/etc.)

4. **Advanced Settings** (collapsible dropdown)
   - Textarea: Edit raw JSON structure
   - Button: "Save Changes"

**Flow:**
1. Navigate to Add Survey from sidebar
2. If no Google connection → show Connect button first
3. Paste edit link → validate format → click Fetch
4. Backend parses form → display preview
5. Optional: Edit JSON for advanced users
6. Save → creates survey in backend → redirect to Surveys page

**Acceptance Criteria:**
- [ ] Invalid link format shows error: "Please paste a valid Google Forms edit link"
- [ ] Fetch button shows loading spinner during API call
- [ ] Preview accordion displays all questions with proper formatting
- [ ] Save creates survey and shows success toast: "Survey added successfully"
- [ ] Advanced JSON editor only visible when toggle clicked

---

### 4. Surveys Management

**Layout:**
- Table similar to dashboard but with additional columns and action buttons per row

**Additional Columns:**
- Contacts Uploaded (count)
- Campaign Status (Idle / Active / Paused)

**Per-Row Actions:**
- "Upload Contacts" button → file picker modal
- "Launch Campaign" / "Pause Campaign" toggle button (changes based on status)

**CSV Upload Modal:**
- File picker: accepts .csv only
- Validation: Must have columns "phone" and "name" (email optional)
- Progress bar during upload
- Success message: "X contacts uploaded"

**Campaign Launch:**
- Confirmation modal: "Launch campaign for [Survey Name]? This will start calling all uploaded contacts."
- After launch, button changes to "Pause Campaign" (orange color)

**Detail View (click survey row):**
- Top: Per-survey metrics cards (same 4 KPIs but filtered for this survey)
- Bottom: Contacts table with columns: Name, Phone, Status (Pending/Called/Responded), Duration

**Flow:**
1. Navigate to Surveys from sidebar
2. See all surveys in table with status
3. Click "Upload Contacts" → select CSV → validate → upload
4. After contacts uploaded, "Launch Campaign" button enables
5. Click Launch → confirm → campaign starts
6. Click survey name → drill down to contact-level details

**Acceptance Criteria:**
- [ ] Upload only accepts .csv files (reject others with error)
- [ ] CSV validation checks required columns before processing
- [ ] Launch button disabled until contacts uploaded
- [ ] Confirmation modal prevents accidental launches
- [ ] Pause button immediately updates campaign status
- [ ] Detail view shows per-contact call status and duration
- [ ] Empty contacts list shows: "Upload contacts to start campaign"

---

### 5. Settings

**Layout:**
- Sidebar + form with configuration options

**Configuration Options:**
1. **Agent Instructions**
   - Textarea: Custom instructions for AI agent behavior
   - Placeholder: "Example: Be friendly and professional..."

2. **Voice Settings**
   - Dropdown: Voice choice (Male / Female options)
   - Dropdown: Tone (Professional / Casual / Enthusiastic)

3. **Notification Preferences** (optional for MVP)
   - Checkbox: Email me when campaign completes

**Flow:**
1. Navigate to Settings
2. Load current settings from backend
3. Modify fields → click "Save Settings"
4. Success toast: "Settings updated successfully"

**Acceptance Criteria:**
- [ ] Current settings pre-populate form on load
- [ ] Agent instructions save and apply to future campaigns
- [ ] Voice/tone dropdowns show all available options
- [ ] Save button shows loading state during update

---

## State Management (Reflex)

### Global State (AppState)
class AppState(rx.State):
# Authentication
is_authenticated: bool = False
user_email: str = ""

text
# Dashboard data
metrics: dict = {}
surveys: list = []

# UI state
is_loading: bool = False
error_message: str = ""
success_message: str = ""
text

### Page-Specific State (SurveyState)
class SurveyState(rx.State):
# Add Survey flow
google_connected: bool = False
form_link: str = ""
fetched_questions: list = []

text
# Surveys page
selected_survey_id: str = ""
contacts: list = []
campaign_status: str = "idle"

# File upload
upload_progress: int = 0
text

**Key Methods (Implement in State classes):**
- `load_dashboard()`: Fetch metrics and surveys on mount
- `fetch_form(link: str)`: Parse Google Form via backend
- `upload_contacts(file)`: Process CSV and save to backend
- `toggle_campaign(survey_id: str)`: Start/pause campaign
- `handle_login(email: str, password: str)`: Authenticate user

---

## Technical Implementation Notes

### Routing Structure
app = rx.App()
app.add_page(landing_page, route="/")
app.add_page(dashboard, route="/dashboard")
app.add_page(add_survey, route="/add_survey")
app.add_page(surveys_list, route="/surveys")
app.add_page(survey_detail, route="/surveys/[id]")
app.add_page(settings, route="/settings")

text

### Backend Integration
- Backend APIs already exist (see PRD2.md for details)
- Use `rx.call_script()` or `httpx` for API calls within State methods
- Pass auth token in headers: `Authorization: Bearer {token}`
- Handle errors gracefully with try/except and display toast messages

### Component Reusability
Create these reusable components to speed development:
- `MetricCard(title, value)`: For dashboard KPIs
- `DataTable(columns, data, on_row_click)`: Sortable table
- `FileUploadModal(on_upload)`: CSV upload with validation
- `ConfirmModal(message, on_confirm)`: Confirmation dialogs
- `Toast(message, type)`: Success/error notifications

### Responsive Design
- Primary target: Desktop (min-width: 1024px)
- Sidebar collapses on mobile (optional for MVP—can skip if time-constrained)
- Tables scroll horizontally on smaller screens

---

## Edge Cases & Error Handling

### Must Handle:
1. **Empty States:**
   - No surveys: Show "Add your first survey" message
   - No contacts: Disable campaign launch with tooltip
   - No data: Display "0" or "—" in metrics

2. **Validation Errors:**
   - Invalid email format on login
   - Invalid Google Forms link (must contain specific URL pattern)
   - CSV missing required columns (phone/name)
   - File size limits (max 5MB for CSV)

3. **API Failures:**
   - Network timeout: Retry button or error message
   - 401 Unauthorized: Redirect to login
   - 500 Server error: Generic error toast

4. **Loading States:**
   - Show spinner during: Login, form fetch, CSV upload, campaign launch
   - Disable action buttons while loading to prevent double-clicks

---

## Branding Assets

**Logo:**
- Use the pear/apple icon from image.jpg (grey #545454 color)
- Place in top nav bar, 24px height
- Text logo: "RESO" in medium weight font next to icon

**Tagline:** "Your Agent for Surveys"

**Favicon:** Use same pear icon, exported as .ico

---

## Implementation Phases (8-Hour Timeline)

### Phase 1: Foundation (2 hours)
- [ ] Set up Reflex project structure
- [ ] Create AppState with auth logic
- [ ] Build landing page + login form
- [ ] Implement navigation bar + sidebar
- [ ] Test login flow with backend

**Checkpoint:** Working authentication

### Phase 2: Dashboard (2 hours)
- [ ] Create dashboard layout with KPI cards
- [ ] Build surveys table component
- [ ] Connect to backend metrics API
- [ ] Implement empty states
- [ ] Add click navigation to survey detail

**Checkpoint:** Dashboard displays data

### Phase 3: Add Survey (2 hours)
- [ ] Create form with Google link input
- [ ] Implement form fetch logic
- [ ] Build question preview accordion
- [ ] Add advanced JSON editor (collapsible)
- [ ] Handle validation errors

**Checkpoint:** Can import Google Form

### Phase 4: Surveys & Campaigns (1.5 hours)
- [ ] Build surveys table with upload/launch buttons
- [ ] Create CSV upload modal with validation
- [ ] Implement campaign toggle (launch/pause)
- [ ] Add confirmation modals
- [ ] Build survey detail view with contacts table

**Checkpoint:** Can upload contacts and launch campaign

### Phase 5: Polish & Settings (0.5 hours)
- [ ] Create settings page with agent config
- [ ] Apply global styles (black/white/grey theme)
- [ ] Add toast notifications for all actions
- [ ] Test all flows end-to-end
- [ ] Fix critical bugs

**Final Checkpoint:** Production-ready MVP

---

## Claude Code Instructions

**Default Behavior:**
- Implement features directly without asking for confirmation
- Use Reflex best practices (rx.State, rx.event handlers)
- Follow exact color scheme and style dicts from Design System section
- Infer missing details from backend PRD2.md context
- Write defensive code with try/except for API calls
- No emojis in UI or code comments
- Use token-efficient code (no verbose docstrings—only essential comments)

**When Uncertain:**
- For styling: Use provided COLORS and style dicts exactly
- For components: Use rx.button, rx.input, rx.data_table, rx.modal
- For routing: Follow structure in Routing Structure section
- For state: Extend AppState and SurveyState classes

**Quality Standards:**
- All buttons must have hover states
- All forms must validate inputs
- All API calls must show loading states
- All errors must display user-friendly messages

---

## Success Criteria

This frontend is ready for production when:
1. ✅ Users can complete full workflow: Login → Add Survey → Upload Contacts → Launch Campaign → View Responses
2. ✅ All 3 success metrics (response length, time saved, total responses) display accurately on dashboard
3. ✅ Design matches reference image aesthetic (clean, professional, iOS-like)
4. ✅ Zero crashes on happy path and common error cases
5. ✅ Works in Chrome/Safari/Firefox on desktop (1024px+ screens)

---

**End of PRD**  
*For backend API details, refer to PRD2.md*  