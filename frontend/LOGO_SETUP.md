# Logo Setup Instructions

## Setup Steps

1. **Copy your logo file** to the assets directory:
   ```bash
   cp /path/to/your/logo2.png frontend/assets/logo2.png
   ```

2. **Reflex will automatically serve** files from the `assets/` directory at the root URL.

3. The logo is now integrated in:
   - ✅ **Navbar** - 40x40px logo with "RESO" branding
   - ✅ **Login Page** - 120x120px centered logo above sign-in
   - ✅ **All Pages** - Via navbar component

## File Locations

- Logo file: `frontend/assets/logo2.png`
- Navbar component: `frontend/frontend/components/navbar.py`
- Login page: `frontend/frontend/pages/login.py`

## Logo Specifications

- **Format:** PNG with transparency
- **Navbar size:** 40x40px
- **Login page size:** 120x120px
- **Recommended:** Square aspect ratio (1:1)

## Testing

After copying the logo:
```bash
cd frontend
reflex run
```

Navigate to:
- Login: http://localhost:3000/login
- Dashboard: http://localhost:3000/dashboard

You should see the RESO logo in the navbar and login page!

## Customization

To change logo sizes, edit:
- `navbar.py` - Change width/height in image component
- `login.py` - Change width/height in image component
