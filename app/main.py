from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
from playwright.sync_api import sync_playwright
from multiprocessing import Pool
import re

app = FastAPI()

def extract_phone(text):
    match = re.search(r'(\+974\s?\d{4}\s?\d{4}|\b\d{4}\s?\d{4}\b)', text)
    if match:
        raw = match.group(0).replace('+974', '').replace(' ', '').strip()
        if len(raw) == 8:
            return '974' + raw
        elif len(raw) == 11 and raw.startswith('974'):
            return raw
    return None

def scrape_single_url(url: str):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(4000)
            text = page.inner_text("body")
            phone = extract_phone(text)
            title = page.title()
            business_name = title.split(" - ")[0].strip()
            page.close()
            browser.close()
            if phone:
                return {"phone": phone, "business": business_name}
            return {"phone": None, "business": business_name}
    except Exception as e:
        return {"error": str(e), "url": url}

class ScrapeRequest(BaseModel):
    links: Union[str, List[str]]

@app.post("/scrape")
def scrape_links(request: ScrapeRequest):
    if isinstance(request.links, str):
        urls = [url.strip() for url in request.links.split(",") if url.strip().startswith("http")]
    else:
        urls = [url.strip() for url in request.links if url.strip().startswith("http")]
    with Pool(processes=6) as pool:
        results = pool.map(scrape_single_url, urls)
    return [r for r in results if r]
