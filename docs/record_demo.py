"""시연 영상 녹화 — 실제 사이트를 Playwright로 조작하며 화면을 기록한다.

실행: /usr/local/bin/python3 record_demo.py [base_url]
출력: /tmp/kspo_video/*.webm
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://kspo.dcselfie.win"
OUT = Path("/tmp/kspo_video")
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("*.webm"):
    old.unlink()


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1280, "height": 860},
            record_video_dir=str(OUT),
            record_video_size={"width": 1280, "height": 860},
            device_scale_factor=1,
        )
        page = context.new_page()
        wait = page.wait_for_timeout

        page.goto(f"{BASE}/", wait_until="load")
        wait(3500)
        page.mouse.wheel(0, 420)
        wait(2500)

        page.get_by_role("link", name="예시 채우기").click()
        page.wait_for_load_state("load")
        wait(3000)
        page.mouse.wheel(0, 320)
        wait(2500)

        page.get_by_role("button", name="같이 갈 수 있는 날 찾기").click()
        page.wait_for_load_state("load")
        wait(4000)
        page.mouse.wheel(0, 520)
        wait(3000)
        page.mouse.wheel(0, -260)
        wait(2000)

        rows = page.locator(".picks a")
        if rows.count() > 1:
            rows.nth(1).click()
            page.wait_for_load_state("load")
            wait(3500)
        page.mouse.wheel(0, 300)
        wait(2500)

        evidence = page.locator("a", has_text="원문 근거 보기").first
        evidence.click()
        page.wait_for_load_state("load")
        wait(3500)
        page.mouse.wheel(0, 640)
        wait(3500)
        page.mouse.wheel(0, 480)
        wait(3000)

        context.close()
        browser.close()

    files = sorted(glob.glob(str(OUT / "*.webm")))
    print("recorded:", files)


if __name__ == "__main__":
    main()
