import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright

MEDIA_CSS_PATH = os.path.join(os.path.dirname(__file__), "test_media.css")
OUTPUT_FOLDER = "saved_pages"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

async def save_page_as_pdf(url):
    uuid = urlparse(url).path.strip("/").split("/")[-1]
    output_path = os.path.join(OUTPUT_FOLDER, f"{uuid}.pdf")
    with open(MEDIA_CSS_PATH, "r") as f:
        custom_css = f.read()

    async with async_playwright() as p:
        browser = await p.firefox.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        # Inject the custom CSS
        await page.add_style_tag(content=custom_css)
        await page.pdf(path=output_path, format="A4", print_background=True)
        await browser.close()
    print(f"Saved PDF to {output_path}")

if __name__ == "__main__":
    url = "https://www.deckenmalerei.eu/0c728050-c5af-11e9-893a-a37e5cdc9651"
    asyncio.run(save_page_as_pdf(url))
