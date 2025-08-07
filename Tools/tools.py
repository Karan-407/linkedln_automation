# import os
# import requests
# from urllib.parse import urlencode
# from dotenv import load_dotenv

# load_dotenv()

# CLIENT_ID = os.getenv("CLIENT_ID")
# CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# REDIRECT_URI = os.getenv("REDIRECT_URI")

# # Step 1: Generate the authorization URL
# def generate_auth_url():
#     params = {
#         "response_type": "code",
#         "client_id": CLIENT_ID,
#         "redirect_uri": REDIRECT_URI,
#         "scope": "r_liteprofile w_member_social"
#     }
#     url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
#     print("👉 Go to this URL in your browser:")
#     print(url)

# # Step 2: Exchange authorization code for access token
# def get_access_token(auth_code):
#     token_url = "https://www.linkedin.com/oauth/v2/accessToken"
#     data = {
#         "grant_type": "authorization_code",
#         "code": auth_code,
#         "redirect_uri": REDIRECT_URI,
#         "client_id": CLIENT_ID,
#         "client_secret": CLIENT_SECRET
#     }
#     response = requests.post(token_url, data=data)
#     response.raise_for_status()
#     return response.json()["access_token"]

# # Step 3: Get your person URN
# def get_person_urn(access_token):
#     headers = {"Authorization": f"Bearer {access_token}"}
#     response = requests.get("https://api.linkedin.com/v2/me", headers=headers)
#     response.raise_for_status()
#     user_id = response.json()["id"]
#     return f"urn:li:person:{user_id}"

# # Step 4: Post content
# def post_to_linkedin(access_token, person_urn, post_text):
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "X-Restli-Protocol-Version": "2.0.0",
#         "Content-Type": "application/json"
#     }

#     post_data = {
#         "author": person_urn,
#         "lifecycleState": "PUBLISHED",
#         "specificContent": {
#             "com.linkedin.ugc.ShareContent": {
#                 "shareCommentary": {"text": post_text},
#                 "shareMediaCategory": "NONE"
#             }
#         },
#         "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
#     }

#     response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=post_data)
#     if response.status_code == 201:
#         print("✅ Post published successfully!")
#     else:
#         print("❌ Failed to post:", response.text)

# # === Run Steps ===
# generate_auth_url()
# auth_code = input("\n🔐 Paste the 'code' from the redirected URL here: ").strip()
# access_token = get_access_token(auth_code)
# person_urn = get_person_urn(access_token)
# post_text = "🚀 Hello world! This is an automated LinkedIn post using Python. #LinkedIn #Python #Automation"

# post_to_linkedin(access_token, person_urn, post_text)

import requests
import os
from dotenv import load_dotenv

load_dotenv()
post_content = "Hi"
def post_to_linkedin(post_content: str):
    """Posts content to LinkedIn using API"""
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.getenv("LINKEDIN_PERSON_URN")

    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": post_content
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
    except Exception as ex:
        print(ex)
    
    return response.json()

post_to_linkedin(post_content)