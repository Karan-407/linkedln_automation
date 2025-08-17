import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# It's safer to check if the environment variables exist
USER_URN = os.getenv("USER_URN")
ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")


def create_linkedin_post(content: str, visibility: str = "PUBLIC"):
    """
    Takes the content as input and posts it to LinkedIn.
    """
    # Check for the presence of necessary credentials
    if not USER_URN or not ACCESS_TOKEN:
        error_msg = "LinkedIn API credentials (USER_URN, ACCESS_TOKEN) are not set in the environment."
        print(f"Error: {error_msg}")
        return {"success": False, "error": error_msg}

    url = "https://api.linkedin.com/rest/posts"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",  # requests handles the charset with the `json` param
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202408",
    }

    # Structure of the post data as per LinkedIn API documentation
    post_data = {
        "author": USER_URN,
        "commentary": content,
        "visibility": visibility,
        "distribution": {"feedDistribution": "MAIN_FEED"},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    try:
        print("\nAttempting to post to LinkedIn...")
        # **KEY FIX**: Use the `json` parameter to let `requests` handle encoding.
        # This is the standard and most reliable way to send JSON data.
        response = requests.post(url, headers=headers, json=post_data)

        # This will raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()
        print("Successfully posted to LinkedIn!")

        # Check if the response has content before trying to parse JSON.
        post_id = None
        if response.text:
            try:
                post_id = response.json().get("id")
            except requests.exceptions.JSONDecodeError:
                print("Warning: Received a non-JSON success response from LinkedIn.")

        return {
            "success": True,
            "post_id": post_id,
            "status_code": response.status_code,
        }
    except requests.exceptions.HTTPError as e:
        error_details = e.response.text if e.response else "No response body"
        status_code = e.response.status_code if e.response else "N/A"
        print(f"HTTP Error posting to LinkedIn: {e}")
        print(f"Response Details: {error_details}")
        return {
            "success": False,
            "error": f"HTTP Error: {status_code}",
            "details": error_details,
        }
    except requests.exceptions.RequestException as e:
        print(f"An unexpected request error occurred: {e}")
        return {"success": False, "error": str(e), "details": None}