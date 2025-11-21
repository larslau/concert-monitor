#!/usr/bin/env python3
"""
Concert Ticket Monitoring System - Advanced Anti-Bot Version
Uses sophisticated techniques to bypass bot detection
"""

import json
import hashlib
import smtplib
import os
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Set, Optional, Tuple
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote, urljoin, urlparse
import time
import random
import cloudscraper  # pip install cloudscraper
from fake_useragent import UserAgent  # pip install fake-useragent
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AdvancedConcertMonitor:
    def __init__(self, config_file='search_config.json'):
        """Initialize the advanced concert monitoring system"""
        self.config = self.load_config(config_file)
        self.results = []
        self.seen_hashes = self.load_seen_hashes()
        self.new_items = []
        self.ua = UserAgent()
        self.scrapers = {}
        self.create_scrapers()
        
    def create_scrapers(self):
        """Create multiple scraper instances with different configurations"""
        # Cloudscraper for Cloudflare bypass
        self.scrapers['cloudflare'] = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        # Standard session with enhanced headers
        session = requests.Session()
        session.headers.update(self.get_enhanced_headers())
        self.scrapers['standard'] = session
        
        # Mobile session
        mobile_session = requests.Session()
        mobile_session.headers.update(self.get_mobile_headers())
        self.scrapers['mobile'] = mobile_session
        
    def get_enhanced_headers(self):
        """Get sophisticated headers that mimic real browser"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,da;q=0.8,de;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Pragma': 'no-cache',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
    def get_mobile_headers(self):
        """Mobile headers for sites that work better on mobile"""
        return {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_file}' not found")
            sys.exit(1)
            
    def load_seen_hashes(self) -> Set[str]:
        """Load previously seen item hashes"""
        try:
            with open('seen_items.json', 'r') as f:
                return set(json.load(f))
        except:
            return set()
            
    def save_seen_hashes(self):
        """Save seen item hashes to file"""
        with open('seen_items.json', 'w') as f:
            json.dump(list(self.seen_hashes), f)
            
    def validate_artist_in_text(self, text: str, artist: str, variations: List[str]) -> bool:
        """Validate that the full artist name appears in the text"""
        text_lower = text.lower()
        
        # Clean text
        text_lower = re.sub(r'\s+', ' ', text_lower)
        
        # Check main artist name
        if artist.lower() in text_lower:
            return True
            
        # Check variations
        for variation in variations:
            if variation.lower() in text_lower:
                return True
                
        return False
        
    def generate_item_hash(self, item: Dict) -> str:
        """Generate unique hash for an item"""
        hash_string = f"{item['artist']}_{item.get('venue', '')}_{item.get('date', '')}_{item.get('city', '')}_{item.get('title', '')}"
        return hashlib.md5(hash_string.encode()).hexdigest()
        
    def extract_price_info(self, text: str) -> Optional[str]:
        """Extract price information from text"""
        price_patterns = [
            r'(?:fra\s*)?(?:kr\.?\s*)?(\d{1,4}(?:[.,]\d{2})?)\s*(?:kr\.?|DKK|,-)',
            r'€\s*(\d{1,4}(?:[.,]\d{2})?)',
            r'£\s*(\d{1,4}(?:[.,]\d{2})?)',
            r'SEK\s*(\d{1,4})',
            r'NOK\s*(\d{1,4})',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
        
    def extract_date_info(self, text: str) -> Optional[str]:
        """Extract date information from text"""
        months = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)'
        
        date_patterns = [
            rf'\d{{1,2}}\.?\s*{months}\s*\d{{2,4}}',
            rf'{months}\s*\d{{1,2}},?\s*\d{{2,4}}',
            r'\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
        
    def advanced_search(self, url: str, site_name: str, artist: str) -> Optional[requests.Response]:
        """Try multiple strategies to get past bot detection"""
        strategies = [
            ('cloudflare', self.scrapers['cloudflare']),
            ('standard', self.scrapers['standard']),
            ('mobile', self.scrapers['mobile']),
        ]
        
        for strategy_name, scraper in strategies:
            try:
                # Random delay
                time.sleep(random.uniform(2, 5))
                
                # Update headers for each request
                if strategy_name == 'standard':
                    scraper.headers.update({'User-Agent': self.ua.random})
                
                # Try to get the page
                response = scraper.get(url, timeout=15, allow_redirects=True, verify=False)
                
                # Check if we got blocked
                if response.status_code == 200:
                    # Check for common blocking indicators in content
                    content = response.text.lower()
                    blocking_indicators = [
                        'access denied',
                        'cloudflare',
                        'please verify you are human',
                        'checking your browser',
                        'enable javascript',
                        'robot check'
                    ]
                    
                    if not any(indicator in content for indicator in blocking_indicators):
                        # Check if we have actual results
                        if artist.lower() in content or len(content) > 1000:
                            print(f" ✓ ({strategy_name})")
                            return response
                        
                elif response.status_code == 403:
                    continue  # Try next strategy
                    
            except Exception as e:
                continue  # Try next strategy
                
        return None
        
    def search_ticketmaster_advanced(self, artist: str, country: str = 'dk') -> List[Dict]:
        """Advanced Ticketmaster search with multiple approaches"""
        results = []
        
        # Try different URL patterns
        url_patterns = [
            f"https://www.ticketmaster.{country}/search?q={quote(artist)}",
            f"https://www.ticketmaster.{country}/discovery/search?q={quote(artist)}",
            f"https://m.ticketmaster.{country}/search?q={quote(artist)}",  # Mobile site
        ]
        
        for url in url_patterns:
            response = self.advanced_search(url, f"Ticketmaster {country.upper()}", artist)
            if response:
                results.extend(self.parse_ticketmaster_response(response, artist, url))
                if results:
                    break
                    
        return results
        
    def parse_ticketmaster_response(self, response, artist, url):
        """Parse Ticketmaster response with multiple strategies"""
        results = []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find JSON-LD structured data first
        json_lds = soup.find_all('script', type='application/ld+json')
        for json_ld in json_lds:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, dict) and data.get('@type') == 'Event':
                    if self.validate_artist_in_text(str(data), artist, []):
                        result = {
                            'artist': artist,
                            'title': data.get('name', ''),
                            'venue': data.get('location', {}).get('name', ''),
                            'date': data.get('startDate', ''),
                            'url': data.get('url', ''),
                            'site': 'Ticketmaster',
                            'status': 'Available'
                        }
                        results.append(result)
            except:
                pass
        
        # Fallback to HTML parsing
        if not results:
            # Multiple possible selectors for Ticketmaster
            selectors_to_try = [
                'div[data-test-id*="event"]',
                'article.event-card',
                'div.event-listing',
                'div.search-result',
                'a[href*="/event/"]',
                'div[class*="event"]',
                'div[class*="Event"]',
            ]
            
            for selector in selectors_to_try:
                containers = soup.select(selector)[:20]
                for container in containers:
                    text = container.get_text()
                    if self.validate_artist_in_text(text, artist, []):
                        result = {
                            'artist': artist,
                            'site': 'Ticketmaster',
                            'search_url': url
                        }
                        
                        # Extract title
                        for tag in ['h3', 'h2', 'h4', 'strong']:
                            title_elem = container.find(tag)
                            if title_elem:
                                result['title'] = title_elem.get_text(strip=True)
                                break
                        
                        # Extract link
                        link = container.find('a', href=True)
                        if link:
                            result['url'] = urljoin(url, link['href'])
                        
                        # Extract date and venue
                        result['date'] = self.extract_date_info(text)
                        result['price'] = self.extract_price_info(text)
                        
                        # Check status
                        if re.search(r'sold\s*out|udsolgt', text, re.IGNORECASE):
                            result['status'] = 'Sold Out'
                        else:
                            result['status'] = 'Available'
                        
                        if result.get('title') or result.get('date'):
                            results.append(result)
                            
        return results
        
    def search_site_advanced(self, site: Dict, artist: str, variations: List[str]) -> List[Dict]:
        """Advanced site search with fallbacks"""
        results = []
        
        # Special handling for known sites
        if 'ticketmaster' in site['name'].lower():
            country_map = {
                'Denmark': 'dk',
                'UK': 'co.uk',
                'Sweden': 'se',
                'Norway': 'no'
            }
            for country_name, country_code in country_map.items():
                if country_name in site['name']:
                    return self.search_ticketmaster_advanced(artist, country_code)
        
        # Build search URL
        search_query = quote(artist)
        search_url = site['search_url'].format(query=search_query)
        
        # Try advanced search
        response = self.advanced_search(search_url, site['name'], artist)
        
        if response:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find events with flexible selectors
            possible_containers = [
                'article', 'div.event', 'div.concert', 'div.show',
                'div[class*="event"]', 'div[class*="concert"]',
                'div[class*="card"]', 'div[class*="item"]',
                'li[class*="event"]', 'a[href*="event"]',
                'div[data-event]', 'div[itemtype*="Event"]'
            ]
            
            for selector in possible_containers:
                containers = soup.select(selector)[:15]
                for container in containers:
                    text = container.get_text()
                    
                    if self.validate_artist_in_text(text, artist, variations):
                        result = {
                            'artist': artist,
                            'site': site['name'],
                            'search_url': search_url
                        }
                        
                        # Extract what we can
                        headings = container.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
                        if headings:
                            result['title'] = headings[0].get_text(strip=True)
                        
                        links = container.find_all('a', href=True)
                        for link in links:
                            if 'event' in link.get('href', '').lower() or 'show' in link.get('href', '').lower():
                                result['url'] = urljoin(search_url, link['href'])
                                break
                        
                        result['date'] = self.extract_date_info(text)
                        result['price'] = self.extract_price_info(text)
                        
                        # Extract venue/location
                        location_keywords = ['venue:', 'at ', 'location:', 'where:']
                        for keyword in location_keywords:
                            if keyword in text.lower():
                                idx = text.lower().index(keyword)
                                venue_text = text[idx:idx+100].split('\n')[0]
                                result['venue'] = venue_text.replace(keyword, '').strip()
                                break
                        
                        if re.search(r'sold\s*out|udsolgt|slutsåld', text, re.IGNORECASE):
                            result['status'] = 'Sold Out'
                        else:
                            result['status'] = 'Available'
                        
                        if result.get('title') or result.get('date'):
                            results.append(result)
                            
        return results
        
    def search_all_sites(self):
        """Search all configured sites for all artists"""
        print("\n🎭 Advanced Concert Search")
        print("=" * 50)
        
        success_count = 0
        fail_count = 0
        
        for artist_config in self.config['artists']:
            artist = artist_config['name']
            variations = artist_config.get('variations', [])
            
            print(f"\n🎤 {artist}")
            print("-" * 40)
            
            for site in self.config['sites']:
                if not site.get('enabled', True):
                    continue
                    
                print(f"  {site['name']}...", end='', flush=True)
                
                try:
                    site_results = self.search_site_advanced(site, artist, variations)
                    
                    if site_results:
                        print(f" ✅ Found {len(site_results)}")
                        success_count += 1
                        
                        for result in site_results:
                            item_hash = self.generate_item_hash(result)
                            if item_hash not in self.seen_hashes:
                                self.new_items.append(result)
                                self.seen_hashes.add(item_hash)
                            self.results.append(result)
                    else:
                        print(" ❌")
                        fail_count += 1
                        
                except Exception as e:
                    print(f" ❌ Error: {str(e)[:30]}")
                    fail_count += 1
                
                # Random delay between sites
                time.sleep(random.uniform(3, 7))
                
                # Rotate user agent periodically
                if (success_count + fail_count) % 5 == 0:
                    for scraper in self.scrapers.values():
                        if hasattr(scraper, 'headers'):
                            scraper.headers['User-Agent'] = self.ua.random
                            
        print(f"\n📊 Results: {success_count} successful, {fail_count} failed")
        
    def group_results_by_artist(self) -> Dict[str, List[Dict]]:
        """Group results by artist"""
        grouped = {}
        for item in self.new_items:
            artist = item['artist']
            if artist not in grouped:
                grouped[artist] = []
            grouped[artist].append(item)
        return grouped
        
    def format_html_email(self) -> str:
        """Format results as HTML email"""
        if not self.new_items:
            return None
            
        grouped = self.group_results_by_artist()
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; margin: 0; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }}
                h1 {{ color: #1a1a1a; border-bottom: 3px solid #667eea; padding-bottom: 15px; }}
                h2 {{ color: #667eea; margin-top: 30px; }}
                .concert {{ background: #f8f9fa; padding: 20px; margin: 15px 0; border-left: 4px solid #667eea; border-radius: 8px; }}
                .concert-title {{ font-weight: bold; font-size: 18px; color: #1a1a1a; margin-bottom: 10px; }}
                .status {{ display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; }}
                .status.available {{ background: #4caf50; color: white; }}
                .status.soldout {{ background: #f44336; color: white; }}
                a {{ color: #667eea; text-decoration: none; font-weight: 500; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎵 Concert Alert: {len(self.new_items)} New Shows</h1>
                <p><strong>{datetime.now().strftime('%B %d, %Y')}</strong></p>
        """
        
        for artist, concerts in grouped.items():
            html += f'<h2>🎤 {artist}</h2>'
            
            for concert in concerts:
                status = concert.get('status', 'Available')
                status_class = 'soldout' if status == 'Sold Out' else 'available'
                
                html += f'''
                <div class="concert">
                    <div class="concert-title">
                        {concert.get('title', concert.get('venue', 'Concert'))}
                        <span class="status {status_class}">{status}</span>
                    </div>
                    <div>
                '''
                
                if concert.get('venue'):
                    html += f"<strong>Venue:</strong> {concert['venue']}<br>"
                if concert.get('date'):
                    html += f"<strong>Date:</strong> {concert['date']}<br>"
                if concert.get('price'):
                    html += f"<strong>Price:</strong> {concert['price']}<br>"
                    
                html += f"<strong>Source:</strong> {concert['site']}<br>"
                
                if concert.get('url'):
                    html += f'<a href="{concert["url"]}">🎫 Get Tickets</a>'
                
                html += '</div></div>'
        
        html += '</div></body></html>'
        return html
        
    def send_email(self, html_content: str):
        """Send email with results"""
        if not html_content:
            print("\n📧 No new items - no email sent")
            return
            
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        email_from = os.environ.get('EMAIL_FROM')
        email_password = os.environ.get('EMAIL_PASSWORD')
        email_to = os.environ.get('EMAIL_TO')
        
        if not all([email_from, email_password, email_to]):
            print(f"\n⚠️  Email config missing - {len(self.new_items)} items not emailed")
            return
            
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f'🎵 {len(self.new_items)} New Concerts - {datetime.now().strftime("%b %d")}'
        
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_from, email_password)
                server.send_message(msg)
                print(f"\n✅ Email sent: {len(self.new_items)} new concerts")
        except Exception as e:
            print(f"\n❌ Email error: {e}")
            
    def run(self):
        """Main execution method"""
        print("🎭 Advanced Concert Monitor v2.0")
        print(f"📅 {datetime.now().strftime('%A, %B %d, %Y at %H:%M')}")
        print("🛡️  Using anti-bot detection measures")
        
        self.search_all_sites()
        
        print(f"\n📈 Final Results:")
        print(f"  Total found: {len(self.results)}")
        print(f"  New concerts: {len(self.new_items)}")
        
        self.save_seen_hashes()
        
        if self.new_items:
            html_email = self.format_html_email()
            self.send_email(html_email)
            
        print("\n✨ Complete!")
        return len(self.new_items)

def main():
    """Main entry point"""
    try:
        # Check for required packages
        required = ['cloudscraper', 'fake-useragent', 'beautifulsoup4', 'requests']
        missing = []
        
        for package in required:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing.append(package)
                
        if missing:
            print(f"⚠️  Installing required packages: {', '.join(missing)}")
            os.system(f"pip install {' '.join(missing)}")
            print("Please run the script again after installation completes.")
            sys.exit(1)
            
        monitor = AdvancedConcertMonitor()
        monitor.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
