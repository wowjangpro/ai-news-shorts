"""YouTube 자동 업로드 모듈 — OAuth 2.0 인증 + 업로드"""
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import CLIENT_SECRET_PATH, TOKEN_PATH, YOUTUBE_CATEGORY

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


class YouTubeUploader:
    """YouTube Data API v3로 영상 업로드"""

    def __init__(self):
        self.service = None

    def authenticate(self):
        """OAuth 2.0 인증 (첫 실행 시 브라우저, 이후 토큰 재사용)"""
        creds = None

        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 토큰 갱신 중...")
                creds.refresh(Request())
            else:
                if not CLIENT_SECRET_PATH.exists():
                    raise FileNotFoundError(f"❌ {CLIENT_SECRET_PATH} 파일이 없습니다.")
                print("🌐 브라우저에서 Google 계정 인증을 진행해주세요...")
                flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
                creds = flow.run_local_server(port=0)

            TOKEN_PATH.write_text(creds.to_json())
            print("✅ 인증 완료")

        self.service = build("youtube", "v3", credentials=creds)
        return self

    def upload(self, video_path: str | Path, script: dict, privacy: str = "public") -> str:
        """영상 업로드 후 video_id 반환

        Args:
            video_path: MP4 파일 경로
            script: news_data.json 데이터 (youtube_title, youtube_description, youtube_tags 사용)
            privacy: private | unlisted | public
        """
        if not self.service:
            self.authenticate()

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"❌ 영상 파일 없음: {video_path}")

        title = script.get("youtube_title", video_path.stem)
        if "#Shorts" not in title:
            title = f"{title} #Shorts"
        description = script.get("youtube_description", "")
        if "#Shorts" not in description:
            description = f"{description}\n\n#Shorts"
        tags = script.get("youtube_tags", [])

        body = {
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
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,
        )

        print(f"📤 업로드 중: {title}")
        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  {pct}% 완료...")

        video_id = response["id"]
        url = f"https://youtu.be/{video_id}"
        print(f"✅ 업로드 완료: {url}")
        print(f"   공개 상태: {privacy}")
        return video_id
