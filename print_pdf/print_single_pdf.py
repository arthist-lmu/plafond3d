import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import logging


MEDIA_CSS_PATH = os.path.join(os.path.dirname(__file__), "test_media.css")
OUTPUT_FOLDER = "print_pdf/saved_pages"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def save_page_as_pdf(url):
    uuid = urlparse(url).path.strip("/").split("/")[-1]
    output_path = os.path.join(OUTPUT_FOLDER, f"{uuid}.pdf")
    logging.info(f"Reading custom CSS from {MEDIA_CSS_PATH}")
    with open(MEDIA_CSS_PATH, "r") as f:
        custom_css = f.read()

    logging.info("Launching Chromium browser with Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        logging.info(f"Navigating to {url}")
        # Increase timeout to 90 seconds (90000 ms)
        await page.goto(url, wait_until="networkidle", timeout=90000)
        logging.info(
            "Injecting custom JavaScript to unfold slick-slider carousels (React)"
        )
        await page.evaluate(
            """
            // Unfold all images in slick-slider carousels (React Slick)
            document.querySelectorAll('.slick-slider').forEach(function(slider) {
                // Show all slides
                slider.querySelectorAll('.slick-slide').forEach(function(slide) {
                    slide.style.display = 'block';
                    slide.style.position = 'static';
                    slide.style.opacity = '1';
                    slide.style.width = 'auto';
                });
                // Hide navigation arrows and dots
                slider.querySelectorAll('.slick-arrow, .slick-dots').forEach(function(el) {
                    el.style.display = 'none';
                });
                // Optionally, remove slick-track transform to prevent horizontal scrolling
                var track = slider.querySelector('.slick-track');
                if (track) {
                    track.style.transform = 'none';
                    track.style.display = 'block';
                }
            });
            // Click all expand/collapse links that control expandedBlock elements
            document.querySelectorAll('.expandLink a').forEach(function(link) {
                if (link.offsetParent !== null) { // Only click visible links
                    link.click();
                }
            });
            // Click all <a> elements with href matching a UUID pattern, but only inside .expandedBlock
            document.querySelectorAll('.expandedBlock a[href]').forEach(function(link) {
                if (/\/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$/.test(link.getAttribute('href'))) {
                    if (link.offsetParent !== null) {
                        link.click();
                    }
                }
            });
        """
        )
        # Wait for any navigation caused by clicking links
        await page.wait_for_load_state("networkidle")
        logging.info("Injecting custom CSS into the page")
        await page.add_style_tag(content=custom_css)
        logging.info(f"Saving page as PDF to {output_path}")
        await page.pdf(path=output_path, format="A4", print_background=True)
        await browser.close()
    logging.info(f"Saved PDF to {output_path}")


if __name__ == "__main__":
    url = "https://www.deckenmalerei.eu/0c728050-c5af-11e9-893a-a37e5cdc9651"
    asyncio.run(save_page_as_pdf(url))
