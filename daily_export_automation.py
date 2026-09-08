"""
Daily automation: logs into TRD GTX, exports Price & Availability to Excel,
and saves it into this same repository at a fixed path. GitHub then serves
that file from a permanent "raw" URL that always reflects the latest version,
committed and pushed automatically by the GitHub Actions workflow.

Requirements:
    pip install playwright
    playwright install chromium

Environment variables (set as GitHub Actions secrets):
    TRD_USERNAME, TRD_PASSWORD
"""

import os
from playwright.sync_api import sync_playwright

# This fixed path is what your permanent link will point to.
DOWNLOAD_PATH = "data/latest_export.xlsx"


def export_from_trd():
    """Logs into TRD GTX and saves the Price & Availability export to DOWNLOAD_PATH."""
    os.makedirs("data", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # --- 1. Log in ---
        page.goto("https://trd.grupatopex.com:5051/client/")
        page.fill("input[name='username']", os.environ["TRD_USERNAME"])
        page.fill("input[name='password']", os.environ["TRD_PASSWORD"])
        page.press("input[name='password']", "Enter")  # submits the form
        page.wait_for_load_state("networkidle")

        # --- 2. Navigate to Price & Availability ---
        page.click("text=Price & Availability")
        page.wait_for_load_state("networkidle")

        # --- 3. Open export dropdown and click "Export all data to Excel" ---
        page.click(".dx-icon-export")  # the export icon button, top right
        with page.expect_download() as download_info:
            page.click("text=Export all data to Excel")
        download = download_info.value
        download.save_as(DOWNLOAD_PATH)

        browser.close()

    return DOWNLOAD_PATH


if __name__ == "__main__":
    path = export_from_trd()
    print(f"Saved export to {path}")
