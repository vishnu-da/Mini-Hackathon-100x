"""Helper script to setup logo in Reflex assets."""
import shutil
from pathlib import Path

# Paths
LOGO_SOURCE = Path("../your_logo.png")  # Update this path
LOGO_DEST = Path("assets/logo2.png")

def setup_logo():
    """Copy logo to assets directory."""
    # Create assets directory if it doesn't exist
    LOGO_DEST.parent.mkdir(exist_ok=True)

    if not LOGO_SOURCE.exists():
        print(f"❌ Logo not found at: {LOGO_SOURCE}")
        print("\n📝 Please update LOGO_SOURCE in this script to point to your logo file")
        return

    # Copy logo
    shutil.copy(LOGO_SOURCE, LOGO_DEST)
    print(f"✅ Logo copied to: {LOGO_DEST}")
    print("\n🎉 Logo setup complete!")
    print("\nThe logo will now appear in:")
    print("  • Navbar (40x40px)")
    print("  • Login page (120x120px)")
    print("\nStart the app with: reflex run")

if __name__ == "__main__":
    setup_logo()
