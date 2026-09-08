"""
Daily automation: log into TRD GTX, export Price & Availability to Excel,
and overwrite the SAME Google Drive file every day (so its link never changes).

One-time setup: run create_drive_file_once() manually, paste the printed link
into System 2 by hand (just once, ever), then save the printed file ID as the
DRIVE_FILE_ID secret. After that, every day only needs export + update_drive_file.

Requirements:
    pip install playwright google-api-python-client google-auth
    playwright install chromium

Environment variables (set as GitHub Actions secrets, never hard-code these):
    TRD_USERNAME, TRD_PASSWORD
    GOOGLE_SERVICE_ACCOUNT_JSON  (contents of the service account key file)
    DRIVE_FILE_ID  (only needed after the one-time setup run)
"""

import os
import json
from playwright.sync_api import sync_playwright
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

DOWNLOAD_PATH = "export.xlsx"


def export_from_trd():
    """Logs into TRD GTX and downloads the Price & Availability export."""
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


def get_drive_service():
    creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def create_drive_file_once(filepath):
    """
    Run this ONCE, manually, the first time only. It creates the Drive file,
    makes it link-viewable, and prints the permanent link and file ID.
    Paste the link into System 2 by hand (one time), and save the file ID
    as the DRIVE_FILE_ID secret for all future automated runs.
    """
    service = get_drive_service()
    file_metadata = {"name": "price_and_availability_export.xlsx"}
    media = MediaFileUpload(
        filepath,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = file["id"]

    service.permissions().create(
        fileId=file_id, body={"role": "reader", "type": "anyone"}
    ).execute()

    print(f"File ID (save this as the DRIVE_FILE_ID secret): {file_id}")
    print(f"Link (paste this into System 2 manually, once): https://drive.google.com/file/d/{file_id}/view")
    return file_id


def update_drive_file(filepath):
    """Runs every day: overwrites the SAME Drive file's content, so the link never changes."""
    service = get_drive_service()
    media = MediaFileUpload(
        filepath,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    file_id = os.environ["DRIVE_FILE_ID"]
    service.files().update(fileId=file_id, media_body=media).execute()
    print("Drive file updated successfully.")


if __name__ == "__main__":
    excel_path = export_from_trd()
    update_drive_file(excel_path)
