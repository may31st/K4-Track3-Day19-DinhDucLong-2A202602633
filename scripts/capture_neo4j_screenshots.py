"""Script to automate taking 3 required screenshots from Neo4j Browser using Playwright."""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("report/img")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--window-size=1600,1000", "--no-sandbox"]
        )
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        print("Navigating to http://localhost:7474...")
        page.goto("http://localhost:7474/browser/", timeout=30000)
        page.wait_for_timeout(3000)

        # Check if login form is present
        password_input = page.query_selector("input[type='password']")
        if password_input:
            print("Logging in to Neo4j...")
            # Check username input if present
            user_input = page.query_selector("input[data-testid='login-username']") or page.query_selector("input[name='username']")
            if user_input:
                user_input.fill("neo4j")
            password_input.fill("password123")
            connect_btn = page.query_selector("button[type='submit']") or page.query_selector("button:has-text('Connect')")
            if connect_btn:
                connect_btn.click()
            page.wait_for_timeout(5000)

        print("Current page title:", page.title())

        # Dismiss tooltip if present
        page.wait_for_timeout(2000)
        dismiss_btn = page.query_selector("button:has-text('Dismiss')")
        if dismiss_btn:
            print("Dismissing onboarding tooltip...")
            dismiss_btn.click()
            page.wait_for_timeout(1000)

        def run_query(query: str, screenshot_path: Path, wait_secs: float = 4.0):
            print(f"Running query: {query[:50]}...")
            # Click query input
            editor = page.query_selector("div.view-lines") or page.query_selector("textarea") or page.query_selector("[contenteditable='true']")
            if editor:
                editor.click()
                # Select all and type query
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(query, delay=10)
                page.keyboard.press("Control+Enter")
            else:
                # Try finding command input
                cmd_input = page.query_selector("input[data-testid='cmd-input']")
                if cmd_input:
                    cmd_input.fill(query)
                    page.keyboard.press("Enter")
            page.wait_for_timeout(int(wait_secs * 1000))
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"Saved screenshot: {screenshot_path}")

        # Clear previous frames
        run_query(":clear", OUTPUT_DIR / "clear.png", wait_secs=1.0)
        (OUTPUT_DIR / "clear.png").unlink(missing_ok=True)

        # 1. Q-A: Count nodes by label
        q_a = "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC;"
        run_query(q_a, OUTPUT_DIR / "kg_count.png", wait_secs=4.0)

        # Clear
        run_query(":clear", OUTPUT_DIR / "clear.png", wait_secs=1.0)
        (OUTPUT_DIR / "clear.png").unlink(missing_ok=True)

        # 2. Q-B: Cross-KB bridge
        q_b = "MATCH p=(:Person)-[:INVOLVED_IN]->(:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(:Article) RETURN p LIMIT 25;"
        run_query(q_b, OUTPUT_DIR / "kg_cross_kb.png", wait_secs=6.0)

        # Clear
        run_query(":clear", OUTPUT_DIR / "clear.png", wait_secs=1.0)
        (OUTPUT_DIR / "clear.png").unlink(missing_ok=True)

        # 3. Q-D: One case with custom person (Trần Thanh Tuấn - án tử hình vụ 36kg ma túy)
        q_d = "MATCH p=(:Person {name:'Trần Thanh Tuấn'})-[:INVOLVED_IN]->(k:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(a:Article) OPTIONAL MATCH q=(k)-[:INVOLVES|LOCATED_IN]->() RETURN p, q LIMIT 20;"
        run_query(q_d, OUTPUT_DIR / "kg_my_case.png", wait_secs=6.0)

        browser.close()
        print("All 3 screenshots captured successfully!")

if __name__ == "__main__":
    main()
