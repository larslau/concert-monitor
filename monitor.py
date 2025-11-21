#!/usr/bin/env python3
"""
Concert Ticket and Tour Date Monitoring System
Monitors multiple ticketing platforms for specified artists
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
from urllib.parse import quote, urljoin
import time

class ConcertMonitor:
    def __init__(self, config_file='search_config.json'):
        """Initialize the concert monitoring system"""
        self.config = self.load_config(config_file)
        self.results = []
        self.seen_hashes = self.load_seen_hashes()
        self.new_items = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_file}' not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)
            
    def load_seen_hashes(self) -> Set[str]:
        """Load previously seen item hashes"""
        try:
            with open('seen_items.json', 'r') as f:
                return set(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return set()
            
    def save_seen_hashes(self):
        """Save seen item hashes to file"""
        with open('seen_items.json', 'w') as f:
            json.dump(list(self.seen_hashes), f)
            
    def validate_artist_in_text(self, text: str, artist: str, variations: List[str]) -> bool:
        """Validate that the full artist name appears in the text"""
        text_lower = text.lower()
        
        # Check main artist name
        if artist.lower() in text_lower:
            return True
            
        # Check variations
        for variation in variations:
            if variation.lower() in text_lower:
                return True
                
        return False
        
    def generate_item_hash(self, item: Dict) -> str:
        """Generate unique hash for an item to detect duplicates"""
        hash_string = f"{item['artist']}_{item['venue']}_{item.get('date', '')}_{item.get('city', '')}"
        return hashlib.md5(hash_string.encode()).hexdigest()
        
    def extract_price_info(self, text: str) -> Optional[str]:
        """Extract price information from text"""
        price_patterns = [
            r'€\s*\d+(?:\.\d{2})?(?:\s*-\s*€?\s*\d+(?:\.\d{2})?)?',
            r'DKK\s*\d+(?:\.\d{2})?(?:\s*-\s*DKK?\s*\d+(?:\.\d{2})?)?',
            r'£\s*\d+(?:\.\d{2})?(?:\s*-\s*£?\s*\d+(?:\.\d{2})?)?',
            r'\d+(?:\.\d{2})?\s*(?:EUR|DKK|GBP|SEK|NOK)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
        
    def extract_date_info(self, text: str) -> Optional[str]:
        """Extract date information from text"""
        # Common date patterns
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{2,4}',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
        
    def search_site(self, site: Dict, artist: str, variations: List[str]) -> List[Dict]:
        """Search a single site for an artist"""
        results = []
        
        # Build search URL
        search_query = quote(artist)
        search_url = site['search_url'].format(query=search_query)
        
        try:
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract results using site-specific selectors
            selectors = site.get('selectors', {})
            
            # Find result containers
            if 'container' in selectors:
                containers = soup.select(selectors['container'])[:15]  # Max 15 results per search
                
                for container in containers:
                    # Validate artist name is present
                    container_text = container.get_text()
                    if not self.validate_artist_in_text(container_text, artist, variations):
                        continue
                    
                    result = {
                        'artist': artist,
                        'site': site['name'],
                        'search_url': search_url
                    }
                    
                    # Extract title
                    if 'title' in selectors:
                        title_elem = container.select_one(selectors['title'])
                        if title_elem:
                            result['title'] = title_elem.get_text(strip=True)
                    
                    # Extract link
                    if 'link' in selectors:
                        link_elem = container.select_one(selectors['link'])
                        if link_elem and link_elem.get('href'):
                            result['url'] = urljoin(response.url, link_elem['href'])
                    
                    # Extract venue
                    if 'venue' in selectors:
                        venue_elem = container.select_one(selectors['venue'])
                        if venue_elem:
                            result['venue'] = venue_elem.get_text(strip=True)
                    elif 'venue' not in result:
                        # Try to extract from text
                        venue_match = re.search(r'(?:at|@|venue:)\s*([^,\n]+)', container_text, re.IGNORECASE)
                        if venue_match:
                            result['venue'] = venue_match.group(1).strip()
                    
                    # Extract city
                    if 'city' in selectors:
                        city_elem = container.select_one(selectors['city'])
                        if city_elem:
                            result['city'] = city_elem.get_text(strip=True)
                    
                    # Extract date
                    if 'date' in selectors:
                        date_elem = container.select_one(selectors['date'])
                        if date_elem:
                            result['date'] = date_elem.get_text(strip=True)
                    elif 'date' not in result:
                        result['date'] = self.extract_date_info(container_text)
                    
                    # Extract price
                    if 'price' in selectors:
                        price_elem = container.select_one(selectors['price'])
                        if price_elem:
                            result['price'] = price_elem.get_text(strip=True)
                    elif 'price' not in result:
                        result['price'] = self.extract_price_info(container_text)
                    
                    # Check if sold out
                    if re.search(r'sold\s*out|udsolgt|slutsåld', container_text, re.IGNORECASE):
                        result['status'] = 'Sold Out'
                    elif re.search(r'presale|pre-sale|forsalg', container_text, re.IGNORECASE):
                        result['status'] = 'Presale'
                    else:
                        result['status'] = 'Available'
                    
                    # Only add if we have minimum required fields
                    if 'title' in result or 'venue' in result:
                        results.append(result)
                        
        except requests.RequestException as e:
            print(f"Error searching {site['name']} for {artist}: {e}")
        except Exception as e:
            print(f"Unexpected error searching {site['name']} for {artist}: {e}")
            
        return results
        
    def search_all_sites(self):
        """Search all configured sites for all artists"""
        for artist_config in self.config['artists']:
            artist = artist_config['name']
            variations = artist_config.get('variations', [])
            
            print(f"Searching for: {artist}")
            
            for site in self.config['sites']:
                if not site.get('enabled', True):
                    continue
                    
                print(f"  Checking {site['name']}...")
                site_results = self.search_site(site, artist, variations)
                
                for result in site_results:
                    # Check for duplicates
                    item_hash = self.generate_item_hash(result)
                    if item_hash not in self.seen_hashes:
                        self.new_items.append(result)
                        self.seen_hashes.add(item_hash)
                    
                    self.results.append(result)
                
                # Rate limiting
                time.sleep(1)
                
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
        
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; }
                h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
                h2 { color: #4CAF50; margin-top: 30px; }
                .concert { background-color: #f9f9f9; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; border-radius: 5px; }
                .concert-title { font-weight: bold; font-size: 16px; color: #333; margin-bottom: 8px; }
                .concert-details { color: #666; line-height: 1.6; }
                .status { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; }
                .status.available { background-color: #4CAF50; color: white; }
                .status.soldout { background-color: #f44336; color: white; }
                .status.presale { background-color: #FF9800; color: white; }
                a { color: #2196F3; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎵 New Concert Alerts - {date}</h1>
                <p>Found {count} new concert(s) matching your criteria:</p>
        """.format(
            date=datetime.now().strftime('%B %d, %Y'),
            count=len(self.new_items)
        )
        
        for artist, concerts in grouped.items():
            html += f'<h2>🎤 {artist}</h2>'
            
            for concert in concerts:
                status_class = 'available'
                if concert.get('status') == 'Sold Out':
                    status_class = 'soldout'
                elif concert.get('status') == 'Presale':
                    status_class = 'presale'
                
                html += f'''
                <div class="concert">
                    <div class="concert-title">
                        {concert.get('title', concert.get('venue', 'Concert'))}
                        <span class="status {status_class}">{concert.get('status', 'Available')}</span>
                    </div>
                    <div class="concert-details">
                '''
                
                if concert.get('venue'):
                    html += f"<strong>Venue:</strong> {concert['venue']}<br>"
                if concert.get('city'):
                    html += f"<strong>City:</strong> {concert['city']}<br>"
                if concert.get('date'):
                    html += f"<strong>Date:</strong> {concert['date']}<br>"
                if concert.get('price'):
                    html += f"<strong>Price:</strong> {concert['price']}<br>"
                
                html += f"<strong>Source:</strong> {concert['site']}<br>"
                
                if concert.get('url'):
                    html += f'<strong>Link:</strong> <a href="{concert["url"]}">View Details & Buy Tickets</a>'
                
                html += '''
                    </div>
                </div>
                '''
        
        html += '''
                <div class="footer">
                    <p>This is an automated alert from your Concert Monitoring System.</p>
                    <p>Monitoring artists: Max Richter, Radiohead, Ludovico Einaudi, and others across Denmark and Europe.</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        return html
        
    def send_email(self, html_content: str):
        """Send email with results"""
        if not html_content:
            print("No new items to report - skipping email")
            return
            
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        email_from = os.environ.get('EMAIL_FROM')
        email_password = os.environ.get('EMAIL_PASSWORD')
        email_to = os.environ.get('EMAIL_TO')
        
        if not all([email_from, email_password, email_to]):
            print("Email configuration missing - skipping email send")
            print(f"Found {len(self.new_items)} new items")
            return
            
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f'🎵 Concert Alert: {len(self.new_items)} New Show(s) Found - {datetime.now().strftime("%b %d")}'
        
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_from, email_password)
                server.send_message(msg)
                print(f"Email sent successfully with {len(self.new_items)} new items")
        except Exception as e:
            print(f"Error sending email: {e}")
            
    def run(self):
        """Main execution method"""
        print(f"Starting concert monitoring - {datetime.now()}")
        print("=" * 50)
        
        # Search all sites
        self.search_all_sites()
        
        print(f"\nTotal results found: {len(self.results)}")
        print(f"New items: {len(self.new_items)}")
        
        # Save seen hashes
        self.save_seen_hashes()
        
        # Send email if new items found
        if self.new_items:
            html_email = self.format_html_email()
            self.send_email(html_email)
        else:
            print("No new items found - no email sent")
            
        print("\nMonitoring complete!")
        return len(self.new_items)

if __name__ == "__main__":
    monitor = ConcertMonitor()
    sys.exit(0 if monitor.run() > 0 else 1)
