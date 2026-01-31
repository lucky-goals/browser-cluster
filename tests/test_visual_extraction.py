import asyncio
import os
import sys

# Setup path to import app modules
sys.path.append(os.getcwd())

from app.core.scraper import Scraper
from playwright.async_api import async_playwright

async def test_extraction():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set a simple HTML content with links
        content = """
        <html>
            <body>
                <div>
                    <h1>Test Page</h1>
                    <a href="https://example.com/item1">Item 1</a>
                    <a href="https://example.com/item2">Item 2</a>
                    <div>
                        <a href="https://example.com/nested">Nested Link</a>
                        <p>Some text</p>
                    </div>
                </div>
            </body>
        </html>
        """
        await page.set_content(content)
        
        scraper = Scraper()
        visual_content = await scraper._extract_visual_content(page)
        
        print("Extracted Visual Content:")
        print("-" * 20)
        print(visual_content)
        print("-" * 20)
        
        # Verification
        assert "Item 1 [Link: https://example.com/item1]" in visual_content
        assert "Item 2 [Link: https://example.com/item2]" in visual_content
        assert "Nested Link [Link: https://example.com/nested]" in visual_content
        
        print("Verification successful! href attributes are correctly captured.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_extraction())
