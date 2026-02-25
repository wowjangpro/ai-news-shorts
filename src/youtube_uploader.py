"""YouTube 자동 업로드 모듈"""
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import CLIENT_SECRET_PATH, TOKEN_PATH, YOUTUBE_CATEGORY


class YouTubeUploader:
    """YouTube Data API v3로 영상 업로드"""

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        privacy: str = "public",
    ) -> str | None:
        """영상 업로드, 성공 시 video_id 반환"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            print("  ⚠️ google-api-python-client 설치 필요:")
            print("  pip install google-api-python-client google-auth-oauthlib")
            return None

        if not CLIENT_SECRET_PATH.exists():
            print(f"  ⚠️ {CLIENT_SECRET_PATH} 파일이 필요합니다.")
            print("  Google Cloud Console → YouTube Data API v3 → OAuth 클라이언트 ID")
            return None

        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

        # 인증
        creds = None
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
            TOKEN_PATH.write_text(creds.to_json())

        youtube = build("youtube", "v3", credentials=creds)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": YOUTUBE_CATEGORY,
                    "defaultLanguage": "ko",
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                },
            },
            media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
        )

        response = request.execute()
        return response.get("id")
