import sys
from pathlib import Path

# Ensure project root is on the path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


def main() -> None:
    print("Python:", sys.version.split()[0])
    print("App name:", settings.app_name)
    print("Database URL:", settings.database_url)
    print("Admin token is set:", bool(settings.admin_token))
    print("Bot token is set:", bool(settings.bot_token))


if __name__ == "__main__":
    main()
