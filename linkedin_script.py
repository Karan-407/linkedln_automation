import requests
import json
from dotenv import load_dotenv
import os
import jwt
import json
import base64

load_dotenv()

URN_NUMBER =os.getenv("USER_URN")
ACCESS_TOKEN=os.getenv("LINKEDIN_ACCESS_TOKEN")

def create_linkedin_post(content, visibility="PUBLIC"):
    """
    Takes the content as the input and post the content to Linkedln
    """
    url = "https://api.linkedin.com/rest/posts"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202408"
    }
    
    post_data = {
        "author": URN_NUMBER,
        "commentary": content,
        "visibility": visibility,
        "distribution": {
            "feedDistribution": "MAIN_FEED"
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=post_data)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "details": e.response.text if hasattr(e, 'response') and e.response else None
        }


