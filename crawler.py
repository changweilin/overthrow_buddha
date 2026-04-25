import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv
import time
from datetime import datetime
import re

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    print("Warning: GEMINI_API_KEY not found. AI features will be disabled.")
    model = None

class DroneIntelCrawler:
    def __init__(self, output_dir="intel_reports"):
        self.output_dir = output_dir
        self.media_dir = os.path.join(output_dir, "media")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        if not os.path.exists(self.media_dir):
            os.makedirs(self.media_dir)

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def clean_filename(self, text):
        return re.sub(r'[\\/*?:"<>|]', "", text).replace(" ", "_")[:50]

    def download_image(self, url, filename):
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                filepath = os.path.join(self.media_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filepath
        except Exception as e:
            self.log(f"Error downloading image {url}: {e}")
        return None

    def analyze_with_ai(self, title, content):
        if not model:
            return "AI Analysis unavailable (API Key missing)."
        
        prompt = f"""
        Analyze the following article about modern drone warfare. 
        Title: {title}
        Content: {content[:3000]}
        
        Provide a structured intelligence report in Markdown:
        1. **Strategic Brief**: A concise 2-3 sentence summary.
        2. **Technical Analysis**: Impact on modern warfare and key technologies mentioned.
        3. **Keywords**: 5-8 relevant tags (e.g., FPV, EW, ISR, NATO).
        4. **Strategic Value**: High/Medium/Low based on tactical innovation.
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            self.log(f"AI Analysis Error: {e}")
            return "AI Analysis failed."

    def scrape_defense_news(self):
        url = "https://www.defensenews.com/unmanned/"
        self.log(f"Scanning {url}...")
        
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.select('article')[:5] # Get latest 5
            
            for art in articles:
                link_tag = art.select_one('a')
                if not link_tag: continue
                
                href = link_tag.get('href')
                if not href.startswith('http'):
                    href = "https://www.defensenews.com" + href
                
                self.process_article(href)
                time.sleep(2) # rate limit
                
        except Exception as e:
            self.log(f"Scraping Error: {e}")

    def process_article(self, url):
        self.log(f"Processing {url}...")
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.select_one('h1').text.strip() if soup.select_one('h1') else "No Title"
            content_div = soup.select_one('.article-body') or soup.select_one('.content')
            content = content_div.text.strip() if content_div else "No Content found."
            
            # Find images
            img_tag = soup.select_one('img')
            img_url = img_tag.get('src') if img_tag else None
            local_img_path = None
            
            if img_url:
                if not img_url.startswith('http'):
                    img_url = "https:" + img_url
                img_ext = os.path.splitext(img_url)[1] or ".jpg"
                img_name = f"img_{self.clean_filename(title)}{img_ext}"
                local_img_path = self.download_image(img_url, img_name)

            # AI Analysis
            ai_report = self.analyze_with_ai(title, content)
            
            # Save Markdown
            report_name = f"intel_{self.clean_filename(title)}.md"
            filepath = os.path.join(self.output_dir, report_name)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"**Source**: {url}\n")
                f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n\n")
                
                if local_img_path:
                    # Use relative path for the MD file
                    rel_img_path = os.path.join("media", os.path.basename(local_img_path))
                    f.write(f"![Header Image]({rel_img_path})\n\n")
                
                f.write(f"## Intelligence Analysis (Gemini AI)\n\n")
                f.write(ai_report + "\n\n")
                
                f.write(f"## Full Content Preview\n\n")
                f.write(content[:1000] + "...\n")
            
            self.log(f"Report saved: {filepath}")
            
        except Exception as e:
            self.log(f"Error processing article: {e}")

if __name__ == "__main__":
    crawler = DroneIntelCrawler()
    crawler.scrape_defense_news()
