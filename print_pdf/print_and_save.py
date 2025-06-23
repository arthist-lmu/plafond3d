import csv
import os
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse

CSV_FILE = 'pages.csv'
OUTPUT_FOLDER = 'saved_pages'

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

async def save_as_pdf(url, output_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until='networkidle')
        await page.pdf(path=output_path, format="A4", print_background=True)
        await browser.close()

async def main():
    with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        tasks = []
        for row in reader:
            url = row.get('pageurl')
            if not url:
                continue
            uuid = urlparse(url).path.strip("/").split("/")[-1]
            output_path = os.path.join(OUTPUT_FOLDER, f"{uuid}.pdf")
            tasks.append(save_as_pdf(url, output_path))
        await asyncio.gather(*tasks)

asyncio.run(main())
