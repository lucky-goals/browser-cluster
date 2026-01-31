import asyncio
import os
import sys

# Setup path to import app modules
sys.path.append(os.getcwd())

from app.core.scraper import Scraper
from playwright.async_api import async_playwright

async def test_coordinates_extraction():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Test Case 1: ll parameter in URL
        content1 = """
        <html>
            <body>
                <a href="https://maps.google.com/maps?ll=-45.033473,168.677683&z=15">Google Map 1</a>
            </body>
        </html>
        """
        await page.set_content(content1)
        
        from app.core.skills import BrowserSkills
        coords1 = await BrowserSkills.extract_coordinates(page)
        print(f"Test Case 1 Result: {coords1}")
        assert coords1['lat'] == '-45.033473'
        assert coords1['lng'] == '168.677683'

        # Test Case 2: @ parameter in URL
        content2 = """
        <html>
            <body>
                <a href="https://www.google.com/maps/@39.9042,116.4074,15z">Google Map 2</a>
            </body>
        </html>
        """
        await page.set_content(content2)
        coords2 = await BrowserSkills.extract_coordinates(page)
        print(f"Test Case 2 Result: {coords2}")
        assert coords2['lat'] == '39.9042'
        assert coords2['lng'] == '116.4074'

        # Test Case 3: query parameter in URL
        content3 = """
        <html>
            <body>
                <a href="https://www.google.com/maps/search/?api=1&query=-33.8688,151.2093">Google Map 3</a>
            </body>
        </html>
        """
        await page.set_content(content3)
        coords3 = await BrowserSkills.extract_coordinates(page)
        print(f"Test Case 3 Result: {coords3}")
        assert coords3['lat'] == '-33.8688'
        assert coords3['lng'] == '151.2093'

        # Test Case 4: No map link
        content4 = "<html><body>No maps here</body></html>"
        await page.set_content(content4)
        coords4 = await BrowserSkills.extract_coordinates(page)
        print(f"Test Case 4 Result: {coords4}")
        assert coords4 is None

        print("All coordinate extraction test cases passed!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_coordinates_extraction())
