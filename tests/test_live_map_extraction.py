import asyncio
import os
import sys
import json

# Setup path to import app modules
sys.path.append(os.getcwd())

from app.core.scraper import Scraper

async def test_live_extraction_with_scraper():
    url = "https://stayhelloqueenstown.guestybookings.com/en/properties/66600784fbb487004a25fe8f"
    
    scraper = Scraper()
    params = {
        "wait_for": "load",
        "wait_time": 10000,
        "stealth": True,
        "interaction_steps": [
            {
                "action": "scroll",
                "params": {"distance": 2000, "selector": "window"}
            },
            {
                "action": "wait",
                "params": {"duration": 5000}
            },
            {
                "action": "extract_coordinates",
                "params": {}
            }
        ]
    }
    
    print(f"Starting scrape for {url}...")
    result = await scraper.scrape(url, params, node_id="test-node")
    
    if result.get("status") == "success":
        skill_results = result.get("skill_results", {})
        coords = skill_results.get("extract_coordinates_2")
        
        if coords:
            print("\n" + "="*30)
            print("EXTRACTION SUCCESSFUL!")
            print(f"Latitude:  {coords.get('lat')}")
            print(f"Longitude: {coords.get('lng')}")
            print(f"Source URL: {coords.get('url')}")
            print("="*30)
        else:
            print("\n" + "="*30)
            print("EXTRACTION FAILED (Skill Result Missing)")
            print(f"Skill Results: {skill_results}")
            print("="*30)
    else:
        print(f"Scrape failed: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_live_extraction_with_scraper())
