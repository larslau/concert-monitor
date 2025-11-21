#!/usr/bin/env python3
"""
Enhanced Multi-Artist and Design Auction Monitor v2
Reads configuration from search_config.json for easy maintenance
"""

import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime
import hashlib
import time
from urllib.parse import quote_plus
import re

class ArtMonitorV2:
    def __init__(self, config_file='search_config.json'):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,da;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache'
        }
        
        # Load configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
            
        self.emailed_items_file = 'emailed_items.json'
        self.active_items_file = 'active_items.json'
        self.load_emailed_items()
        self.load_active_items()
        
    def load_emailed_items(self):
        """Load items that have already been emailed"""
        try:
            with open(self.emailed_items_file, 'r') as f:
                self.emailed_items = json.load(f)
        except:
            self.emailed_items = {}
            
    def save_emailed_items(self):
        """Save emailed items to file"""
        with open(self.emailed_items_file, 'w') as f:
            json.dump(self.emailed_items, f, indent=2)
    
    def load_active_items(self):
        """Load all active items for weekly summary"""
        try:
            with open(self.active_items_file, 'r') as f:
                self.active_items = json.load(f)
        except:
            self.active_items = {}
            
    def save_active_items(self):
        """Save active items to file"""
        with open(self.active_items_file, 'w') as f:
            json.dump(self.active_items, f, indent=2)
    
    def get_item_hash(self, item_data):
        """Create unique hash for an item"""
        # Use title, URL, and search term for uniqueness
        item_str = f"{item_data.get('title', '')}_{item_data.get('url', '')}_{item_data.get('search_term', '')}"
        return hashlib.md5(item_str.encode()).hexdigest()
    
    def validate_result(self, item_title, search_term):
        """Validate that the result actually contains the search terms"""
        title_lower = item_title.lower()
        
        if isinstance(search_term, dict):
            # For furniture: must contain ALL terms
            terms = search_term.get('terms', [])
            if len(terms) >= 2:
                # Check if all terms are present (allow for variations)
                for term in terms:
                    term_lower = term.lower()
                    # Check various formats
                    if not (term_lower in title_lower or 
                           term_lower.replace(' ', '') in title_lower or
                           term_lower.replace('-', '') in title_lower):
                        return False
                return True
            else:
                # Single term search
                return terms[0].lower() in title_lower if terms else False
        else:
            # For artists: must contain the full name
            search_lower = search_term.lower()
            
            # Check if the full artist name is present
            if ' ' in search_term:
                # For names with spaces, check if full name is present
                return search_lower in title_lower
            else:
                # For single word searches
                return search_lower in title_lower
    
    def fix_url(self, url, base_url):
        """Fix malformed URLs"""
        if not url:
            return None
            
        # Remove x-webdoc:// prefix if present
        if url.startswith('x-webdoc://'):
            url = url.replace('x-webdoc://', 'https://')
            
        # Ensure proper URL format
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = base_url.rstrip('/') + url
        elif not url.startswith('http'):
            url = base_url.rstrip('/') + '/' + url
            
        return url
    
    def extract_items_from_html(self, soup, site_name, base_url):
        """Extract items from HTML based on site patterns"""
        items = []
        
        # Site-specific selectors
        site_selectors = {
            'ebay': {
                'container': ['div.s-item__wrapper', 'li.s-item'],
                'title': ['h3.s-item__title', 'span.s-item__title'],
                'link': ['a.s-item__link']
            },
            'lauritz': {
                'container': ['div.lot-card', 'article.lot-card', 'div.ListingCard'],
                'title': ['h3', 'h2', '.lot-title', 'a'],
                'link': ['a']
            },
            'barnebys': {
                'container': ['.item', '.product-card', '.lot-card', 'article'],
                'title': ['h2', 'h3', 'h4', '.title'],
                'link': ['a']
            },
            'bruun': {
                'container': ['.lot-item', '.auction-item', 'article'],
                'title': ['h3', '.lot-title', '.title'],
                'link': ['a']
            },
            'dba': {
                'container': ['.listing-item', 'tr[data-href]', 'article'],
                'title': ['.listing-heading', 'a.listingLink'],
                'link': ['a.listing-heading', 'a.listingLink']
            },
            'default': {
                'container': ['article', 'div.item', 'div.lot', 'li.result'],
                'title': ['h1', 'h2', 'h3', 'a.title', '.title', '.item-title'],
                'link': ['a']
            }
        }
        
        # Determine which selectors to use
        site_key = 'default'
        for key in site_selectors.keys():
            if key != 'default' and key in site_name.lower():
                site_key = key
                break
                
        selectors = site_selectors[site_key]
        
        # Try to find items using various selectors
        containers = []
        for selector in selectors['container']:
            containers = soup.select(selector)
            if containers:
                break
                
        if not containers:
            # Fallback: try to find any likely item containers
            containers = soup.find_all(['article', 'div'], 
                class_=re.compile(r'(item|lot|listing|product|result)', re.I))[:30]
        
        for container in containers[:30]:  # Get more initially for validation
            item_data = {}
            
            # Extract title
            for title_sel in selectors['title']:
                if '.' in title_sel or '[' in title_sel:
                    title_elem = container.select_one(title_sel)
                else:
                    title_elem = container.find(title_sel)
                    
                if title_elem:
                    item_data['title'] = title_elem.get_text(strip=True)
                    break
            
            # Extract link
            for link_sel in selectors['link']:
                if '.' in link_sel or '[' in link_sel:
                    link_elem = container.select_one(link_sel)
                else:
                    link_elem = container.find(link_sel)
                    
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    item_data['url'] = self.fix_url(href, base_url)
                    break
            
            # Only add if we have both title and URL
            if item_data.get('title') and item_data.get('url'):
                items.append(item_data)
                
        return items[:20]  # Limit to 20 items before validation
    
    def search_site(self, site_config, search_term):
        """Search a single site for a term"""
        results = []
        
        try:
            # Build search query
            if isinstance(search_term, dict):
                # Furniture search with multiple terms
                query = ' '.join(search_term['terms'])
                display_term = ' + '.join(search_term['terms'])
            else:
                # Simple artist search
                query = search_term
                display_term = search_term
            
            # Build search URL
            search_url = site_config['search_url'].format(query=quote_plus(query))
            
            print(f"  Searching {site_config['name']} for '{display_term}'...")
            
            # Make request with timeout
            response = requests.get(search_url, headers=self.headers, timeout=15)
            
            # Skip if we get blocked
            if response.status_code == 403:
                print(f"    Access denied (403)")
                return results
            elif response.status_code == 404:
                print(f"    Invalid URL (404)")
                return results
                
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract items
            items = self.extract_items_from_html(soup, site_config['name'], site_config['base_url'])
            
            # Validate and add metadata to each item
            validated_count = 0
            for item in items:
                # Validate that the item actually contains our search terms
                if self.validate_result(item['title'], search_term):
                    item['source'] = site_config['name']
                    item['search_term'] = display_term
                    item['region'] = site_config.get('region', 'Unknown')
                    results.append(item)
                    validated_count += 1
                    if validated_count >= 10:  # Max 10 validated items per search
                        break
                    
            print(f"    Found {validated_count} valid items (from {len(items)} results)")
            
        except requests.exceptions.Timeout:
            print(f"    Timeout")
        except requests.exceptions.RequestException as e:
            print(f"    Network error: {type(e).__name__}")
        except Exception as e:
            print(f"    Unexpected error: {e}")
            
        return results
    
    def check_all_sites(self):
        """Check all configured sites for all search terms"""
        all_results = []
        total_searches = len(self.config['artists']) + len(self.config['furniture'])
        total_sites = len(self.config['sites'])
        
        print(f"\n🔍 Starting search: {total_searches} terms across {total_sites} sites")
        print("=" * 60)
        
        # Search for artists
        print("\n📸 Searching for artists...")
        for artist in self.config['artists']:
            print(f"\n🎨 Artist: {artist}")
            for site in self.config['sites']:
                results = self.search_site(site, artist)
                all_results.extend(results)
                time.sleep(1)  # Rate limiting
                
        # Search for furniture
        print("\n🪑 Searching for furniture...")
        for furniture in self.config['furniture']:
            print(f"\n🛋️ Furniture: {' + '.join(furniture['terms'])} ({furniture['description']})")
            for site in self.config['sites']:
                results = self.search_site(site, furniture)
                all_results.extend(results)
                time.sleep(1)  # Rate limiting
                
        print("\n" + "=" * 60)
        print(f"✅ Search complete: Found {len(all_results)} total items")
        
        return all_results
    
    def filter_new_items(self, items):
        """Filter out items that have already been emailed"""
        new_items = []
        duplicate_count = 0
        
        for item in items:
            item_hash = self.get_item_hash(item)
            if item_hash not in self.emailed_items:
                new_items.append(item)
                self.emailed_items[item_hash] = {
                    'date': datetime.now().isoformat(),
                    'title': item['title'][:100],  # Truncate long titles
                    'source': item['source']
                }
            else:
                duplicate_count += 1
                
            # Update active items list (for weekly summary)
            self.active_items[item_hash] = {
                'title': item['title'],
                'url': item['url'],
                'source': item['source'],
                'search_term': item['search_term'],
                'region': item.get('region', 'Unknown'),
                'last_seen': datetime.now().isoformat()
            }
                
        print(f"📊 Filtered: {len(new_items)} new items, {duplicate_count} duplicates removed")
        return new_items
    
    def create_email_html(self, items):
        """Create beautiful HTML email with results"""
        # Check if it's Sunday for weekly summary
        is_sunday = datetime.now().weekday() == 6
        
        if not items and not is_sunday:
            return None
            
        # Group new items by category (Artists vs Wegner Furniture)
        grouped = {}
        
        for item in items:
            term = item['search_term']
            
            # Determine category
            if any(x in term for x in ['Wegner', 'PP', 'JH', 'Cow Horn', 'Peacock', 'Påfugl']):
                category = 'Wegner Furniture'
            else:
                # Use artist name as category
                category = term
                
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)
        
        # Prepare weekly summary if it's Sunday
        weekly_items = {}
        if is_sunday:
            for item_hash, item_data in self.active_items.items():
                category = 'Wegner Furniture' if any(x in item_data['search_term'] for x in ['Wegner', 'PP', 'JH', 'Cow Horn', 'Peacock', 'Påfugl']) else item_data['search_term']
                if category not in weekly_items:
                    weekly_items[category] = []
                weekly_items[category].append(item_data)
        
        # Sort groups by number of items (most items first)
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                    line-height: 1.6;
                    color: #2c3e50;
                    background: #f5f7fa;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .summary {{
                    background: #fafbfc;
                    padding: 20px 30px;
                    border-bottom: 2px solid #e1e4e8;
                }}
                .content {{
                    padding: 30px;
                }}
                h2 {{
                    color: #667eea;
                    font-size: 20px;
                    margin-top: 30px;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #f0f0f0;
                }}
                .item {{
                    background: #fafbfc;
                    border: 1px solid #e1e4e8;
                    padding: 15px;
                    margin: 12px 0;
                    border-radius: 8px;
                    transition: all 0.3s ease;
                }}
                .item:hover {{
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    transform: translateY(-2px);
                }}
                .item-title {{
                    font-weight: 600;
                    color: #2c3e50;
                    margin-bottom: 8px;
                    font-size: 16px;
                }}
                .item-meta {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 10px;
                }}
                .item-source {{
                    color: #6c757d;
                    font-size: 13px;
                }}
                .item-region {{
                    display: inline-block;
                    background: #e3e8ee;
                    color: #586069;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    margin-left: 8px;
                }}
                .item-search {{
                    color: #95a5a6;
                    font-size: 11px;
                    font-style: italic;
                    margin-top: 4px;
                }}
                a.item-link {{
                    background: #667eea;
                    color: white !important;
                    text-decoration: none;
                    padding: 6px 16px;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: 500;
                    display: inline-block;
                }}
                a.item-link:hover {{
                    background: #5a67d8;
                }}
                .footer {{
                    background: #fafbfc;
                    padding: 30px;
                    text-align: center;
                    color: #6c757d;
                    font-size: 13px;
                    border-top: 2px solid #e1e4e8;
                }}
                .stats {{
                    display: flex;
                    justify-content: space-around;
                    margin-top: 15px;
                }}
                .stat {{
                    text-align: center;
                }}
                .stat-number {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #667eea;
                }}
                .stat-label {{
                    font-size: 12px;
                    color: #6c757d;
                    text-transform: uppercase;
                    margin-top: 5px;
                }}
                .weekly {{
                    background: #fff9e6;
                    border-left-color: #ffc107;
                }}
                .weekly-header {{
                    background: #ffc107;
                    color: #000;
                    padding: 15px;
                    margin: 30px 0 10px 0;
                    border-radius: 4px;
                }}
                .weekly-header h2 {{
                    margin: 0;
                    color: #000;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎨 Art & Design Monitor Alert</h1>
                </div>
                
                <div class="summary">
                    <strong>{}</strong>
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-number">{}</div>
                            <div class="stat-label">New Items</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{}</div>
                            <div class="stat-label">Categories</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{}</div>
                            <div class="stat-label">Sites Checked</div>
                        </div>
                    </div>
                </div>
                
                <div class="content">
        """.format(
            datetime.now().strftime('%B %d, %Y at %I:%M %p'),
            len(items),
            len(grouped),
            len(set(item['source'] for item in items))
        )
        
        for category, term_items in sorted_groups:
            # Sort items within group by source
            term_items.sort(key=lambda x: x['source'])
            
            if category == 'Wegner Furniture':
                html += f'<h2>🪑 {category} ({len(term_items)} items)</h2>'
            else:
                html += f'<h2>🎨 {category} ({len(term_items)} items)</h2>'
            
            for item in term_items:
                # Truncate long titles
                title = item['title']
                if len(title) > 100:
                    title = title[:97] + '...'
                    
                html += f"""
                <div class="item">
                    <div class="item-title">{title}</div>
                    <div class="item-meta">
                        <div>
                            <span class="item-source">📍 {item['source']}</span>
                            <span class="item-region">{item.get('region', 'Unknown')}</span>
                        </div>
                        <a href="{item['url']}" target="_blank" class="item-link">View Item →</a>
                    </div>
                    """
                    
                # Show specific search for Wegner items
                if category == 'Wegner Furniture':
                    html += f'<div class="item-search">Search: {item["search_term"]}</div>'
                    
                html += '</div>'
        
        html += """
                </div>
                
                <div class="footer">
                    <p><strong>Search Configuration:</strong></p>
                    <p>Artists: Agnes Denes, Trine Søndergaard, Nicolai Howalt, and others</p>
                    <p>Furniture: Wegner PP/JH series (PP505 Cow Horn, PP75, PP101, PP550 Peacock)</p>
                    <p style="margin-top: 20px; color: #6c757d;">
                        This automated monitor checks {} sites daily for your specified searches.<br>
                        Only new items are included in each alert.
                    </p>
                    """.format(len(self.config['sites']))
        
        if is_sunday:
            html += '<p><strong>📅 Weekly summaries are sent every Sunday with all active listings.</strong></p>'
            
        html += """
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_email(self, html_content):
        """Send email with results"""
        if not html_content:
            print("📭 No new items to email")
            return False
            
        sender = os.environ.get('SENDER_EMAIL')
        password = os.environ.get('EMAIL_PASSWORD')
        recipient = os.environ.get('RECIPIENT_EMAIL', sender)
        
        if not sender or not password:
            print("❌ Email credentials not configured")
            print("   Set SENDER_EMAIL and EMAIL_PASSWORD environment variables")
            return False
            
        msg = MIMEMultipart('alternative')
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f'🎨 Art & Design Alert - {datetime.now().strftime("%B %d")}'
        
        # Create plain text version
        text = f"""
        New Art & Design Listings Found
        ================================
        
        Date: {datetime.now().strftime('%B %d, %Y')}
        
        Please view this email in HTML format for the best experience.
        
        --
        Art & Design Monitor
        """
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
            print(f"✉️ Email sent successfully to {recipient}")
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    def run(self):
        """Main execution"""
        print("\n" + "=" * 60)
        print("🚀 ART & DESIGN MONITOR v2.0")
        print("=" * 60)
        print(f"⏰ Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if it's Sunday
        is_sunday = datetime.now().weekday() == 6
        if is_sunday:
            print("📅 Today is Sunday - Weekly summary will be included")
        
        # Load configuration summary
        print(f"\n📋 Configuration loaded:")
        print(f"  • {len(self.config['artists'])} artists to search")
        print(f"  • {len(self.config['furniture'])} furniture items to search")
        print(f"  • {len(self.config['sites'])} sites to check")
        
        # Check all sites
        all_items = self.check_all_sites()
        
        # Filter new items
        new_items = self.filter_new_items(all_items)
        
        # Save active items (for weekly summary)
        self.save_active_items()
        
        if new_items or is_sunday:
            print(f"\n🎉 Found {len(new_items)} new items!")
            
            # Create and send email
            html = self.create_email_html(new_items)
            if self.send_email(html):
                # Save state only if email was sent successfully
                self.save_emailed_items()
                print("💾 State saved successfully")
                
            if is_sunday:
                print("📅 Weekly summary included in email")
        else:
            print("\n😴 No new items found")
        
        print(f"\n⏰ Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

if __name__ == "__main__":
    monitor = ArtMonitorV2()
    monitor.run()
