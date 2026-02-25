"""뉴스 크롤링 & AI 요약 모듈"""
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import ANTHROPIC_API_KEY, TEMPLATES_DIR


class NewsFetcher:
    """뉴스 기사를 가져와 쇼츠 스크립트로 변환"""

    def fetch_from_url(self, url: str) -> str:
        """URL에서 기사 본문 추출"""
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 일반적인 기사 본문 셀렉터
        selectors = [
            "article", "#article-body", ".article_body",
            "#newsct_article", ".news_end", "#articeBody",
            ".article-body", "#news_body", ".story-body",
        ]
        text = ""
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator="\n", strip=True)
                break

        if not text:
            # fallback: 모든 <p> 태그
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # 정리
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:5000]  # 토큰 제한

    def fetch_top_news(self) -> str:
        """오늘의 주요 뉴스 자동 수집 (네이버 뉴스 기준)"""
        url = "https://news.naver.com/main/ranking/popularDay.naver"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            # 첫 번째 랭킹 기사 링크
            link = soup.select_one(".rankingnews_list a")
            if link and link.get("href"):
                return self.fetch_from_url(link["href"])
        except Exception as e:
            print(f"  ⚠️ 자동 수집 실패: {e}")

        # fallback: 수동 입력
        print("  📝 기사 URL을 입력하세요:")
        url = input("  > ").strip()
        return self.fetch_from_url(url)

    def summarize_to_script(self, article_text: str) -> dict:
        """기사를 6개 씬 쇼츠 스크립트로 변환"""
        
        # Claude API 사용
        if ANTHROPIC_API_KEY:
            return self._summarize_with_claude(article_text)

        # API 없으면 간단한 룰 기반 분할
        return self._summarize_rule_based(article_text)

    def _summarize_with_claude(self, article_text: str) -> dict:
        """Claude API로 요약"""
        prompt_template = (TEMPLATES_DIR / "news_prompt.txt").read_text()
        prompt = prompt_template.replace("{article_text}", article_text)

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"]

        # JSON 추출
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # JSON 블록 없이 바로 JSON인 경우
        return json.loads(content)

    def _summarize_rule_based(self, article_text: str) -> dict:
        """룰 기반 간단 분할 (API 없을 때 fallback)"""
        lines = [l.strip() for l in article_text.split("\n") if l.strip() and len(l.strip()) > 10]
        
        # 6개 씬으로 균등 분할
        chunk_size = max(1, len(lines) // 6)
        scenes = []
        tags = ["속보", "배경", "상세", "영향", "반응", "전망"]
        
        for i in range(6):
            start = i * chunk_size
            end = start + chunk_size
            chunk = lines[start:end]
            text = " ".join(chunk)[:100]

            # 자막: 30자 단위로 줄바꿈
            subtitle_lines = []
            words = text.split()
            current_line = ""
            for w in words:
                if len(current_line) + len(w) > 15:
                    subtitle_lines.append(current_line)
                    current_line = w
                    if len(subtitle_lines) >= 3:
                        break
                else:
                    current_line = f"{current_line} {w}".strip()
            if current_line and len(subtitle_lines) < 3:
                subtitle_lines.append(current_line)

            scenes.append({
                "tag": tags[i],
                "subtitle": "\n".join(subtitle_lines),
                "tts_text": text,
                "image_prompt": f"Realistic news photo, Korean financial district, scene {i+1}",
                "duration": 6,
            })

        title = lines[0][:15] if lines else "오늘의 뉴스"
        
        return {
            "title": title,
            "youtube_title": f"[속보] {title} | {__import__('datetime').datetime.now().strftime('%Y.%m.%d')}",
            "youtube_description": f"{article_text[:200]}...\n\n#뉴스 #속보 #오늘의뉴스",
            "youtube_tags": ["뉴스", "속보", "오늘의뉴스", "시사"],
            "scenes": scenes,
        }


if __name__ == "__main__":
    # 테스트
    fetcher = NewsFetcher()
    print("URL을 입력하세요:")
    url = input("> ").strip()
    article = fetcher.fetch_from_url(url)
    print(f"\n기사 길이: {len(article)}자")
    print(article[:500])
    
    script = fetcher.summarize_to_script(article)
    print(json.dumps(script, ensure_ascii=False, indent=2))
