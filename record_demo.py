import asyncio
import os
import sys
from playwright.async_api import async_playwright

FRONTEND_URL = "http://localhost:8080"
OUTPUT_VIDEO = "/config/.gemini/antigravity/brain/e7fc7751-842c-4c0b-b27a-33e1ba99695c/demo.webm"

async def record_demo():
    print(f"Starting Playwright browser recording on {FRONTEND_URL}...")
    os.makedirs("/tmp/playwright_videos", exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir="/tmp/playwright_videos",
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        print("Navigating to frontend...")
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await asyncio.sleep(2)

        # Prompt 1: What the app does best (AI Governance & Shadow Agent Audit)
        prompt1 = "Audit our agent estate across Google Cloud. Discover any shadow agents and check their identity and IAM roles."
        print(f"Typing Prompt 1: {prompt1}")
        input_box = page.locator("#input")
        await input_box.fill(prompt1)
        await asyncio.sleep(1)

        # Submit form
        await page.locator("button[type='submit']").click()
        print("Sent Prompt 1. Waiting for agent response...")

        try:
            await page.wait_for_selector(".msg.agent", timeout=35000)
            print("Received Prompt 1 response!")
            await asyncio.sleep(6)  # Pause to display response on video
        except Exception as e:
            print(f"Waiting for Prompt 1: {e}")

        # Prompt 2: Richer prompt showing tool calls, database lookups, generated image, and memory bank saving
        prompt2 = "Generate an official AI Security Audit Badge image for our estate, and save my preference: 'Security audit reports must be archived to GCS monthly'."
        print(f"Typing Prompt 2: {prompt2}")
        await input_box.fill(prompt2)
        await asyncio.sleep(1)

        await page.locator("button[type='submit']").click()
        print("Sent Prompt 2. Waiting for agent response with badge image and memory saving...")

        try:
            # Wait for 2 agent messages to be present
            await page.wait_for_selector(".msg.agent:nth-of-type(2)", timeout=45000)
            print("Received Prompt 2 response!")
            await asyncio.sleep(8)  # Pause to show generated image & memory confirmation
        except Exception as e:
            print(f"Waiting for Prompt 2: {e}")
            await asyncio.sleep(5)

        recorded_path = await page.video.path()
        print(f"Playwright video recorded at: {recorded_path}")
        await context.close()
        await browser.close()

        # Copy to artifact directory
        os.system(f"cp '{recorded_path}' '{OUTPUT_VIDEO}'")
        print(f"Demo video successfully saved to: {OUTPUT_VIDEO}")
        return OUTPUT_VIDEO

if __name__ == "__main__":
    asyncio.run(record_demo())
