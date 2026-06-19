#!/usr/bin/env python3
"""batch_*.json 검증: JSON 파싱 + 깨진 문자(�) + 제목/씬/길이 출력."""
import json
from pathlib import Path


def count_broken(obj) -> int:
    if isinstance(obj, str):
        return obj.count("�")
    if isinstance(obj, dict):
        return sum(count_broken(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(count_broken(v) for v in obj)
    return 0


def main() -> None:
    files = sorted(Path(__file__).parent.glob("batch_*.json"))
    print(f"총 {len(files)}개 batch 파일\n")
    total_broken = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ {f.name}: JSON 파싱 실패 — {e}")
            total_broken += 1
            continue
        broken = count_broken(data)
        total_broken += broken
        scenes = data.get("scenes", [])
        dur = sum(s.get("duration", 0) for s in scenes)
        # highlight_lines 인덱스 유효성 체크
        bad_hl = []
        for i, s in enumerate(scenes):
            n_lines = len(s.get("subtitle", "").split("\n"))
            for hl in s.get("highlight_lines", []):
                if hl >= n_lines or hl < 0:
                    bad_hl.append(f"scene{i}:hl{hl}/{n_lines}")
        flag = "⚠️" if (broken or bad_hl) else "✅"
        print(f"{flag} {f.name} | 제목: {data.get('title','')!r} | 씬 {len(scenes)}개 | {dur}초 | 깨짐 {broken}"
              + (f" | HL오류 {bad_hl}" if bad_hl else ""))
    print(f"\n총 깨진 문자: {total_broken}")
    if total_broken == 0:
        print("✅ 모든 파일 한글 정상 (깨짐 없음)")


if __name__ == "__main__":
    main()
