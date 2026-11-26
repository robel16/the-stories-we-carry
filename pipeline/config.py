
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


def get_cloudflare_credentials() -> tuple[str, str]:
    """Return Cloudflare Account ID and API token."""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()

    if not account_id or not api_token:
        raise RuntimeError(
            "Cloudflare credentials are missing. "
            "Check CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env."
        )

    return account_id, api_token


def get_gemini_api_key() -> str:
    """Return the Google AI Studio API key."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "Gemini API key is missing. Check GEMINI_API_KEY in .env."
        )

    return api_key


def check_credentials() -> dict[str, bool]:
    """Check credential availability without exposing secret values."""
    return {
        "cloudflare": bool(
            os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
            and os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
        ),
        "gemini": bool(os.getenv("GEMINI_API_KEY", "").strip()),
    }


if __name__ == "__main__":
    print("\n=== GENERATION PROVIDER CONFIGURATION ===")

    for provider, configured in check_credentials().items():
        status = "CONFIGURED" if configured else "MISSING"
        print(f"{provider.capitalize()}: {status}")

    print("=========================================\n")
