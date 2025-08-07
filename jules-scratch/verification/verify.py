import asyncio
from playwright.async_api import async_playwright, expect

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Listen for console events and print them
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))

        # Navigate to the local server
        await page.goto("http://localhost:8000")

        # Wait for the loading screen to disappear
        loading_screen = page.locator("#loading-screen")
        await expect(loading_screen).to_be_hidden(timeout=30000)

        # Give a little extra time for the scene to render fully
        await page.wait_for_timeout(2000)

        # Take a screenshot
        await page.screenshot(path="jules-scratch/verification/verification.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
