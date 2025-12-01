import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime

class NOCIXScraper:
    def __init__(self):
        self.base_url = "https://www.nocix.net"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.urls = [
            "https://www.nocix.net/dedicated/",
            "https://www.nocix.net/custom-dedicated-servers/",
            "https://www.nocix.net/game-dedicated-servers/",
            "https://www.nocix.net/enterprise-dedicated-servers/",
            "https://www.nocix.net/high-performance-dedicated-servers/",
            "https://www.nocix.net/legacy-and-budget-dedicated-servers/"
        ]
    
    def fetch_page(self, url):
        """Fetch page content with error handling"""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_text_clean(self, element):
        """Extract and clean text from element"""
        if element:
            text = element.get_text(separator='\n', strip=True)
            text = re.sub(r'\n+', '\n', text)
            text = re.sub(r' +', ' ', text)
            return text
        return ""
    
    def parse_price(self, text):
        """Extract price from text"""
        if not text:
            return ""
        price_match = re.search(r'\$(\d+(?:\.\d{2})?)\s*(?:/\s*month|/mo)?', text, re.IGNORECASE)
        if price_match:
            return f"${price_match.group(1)}/month"
        return ""
    
    def parse_included_column(self, text):
        """Parse the 'Included' column for all details"""
        details = {
            'bandwidth': '',
            'port_speed': '',
            'ipv4_addresses': '',
            'ipv6_addresses': '',
            'instant_deployment': False,
            'free_setup': False,
            'location': '',
            'additional_features': []
        }
        
        if not text:
            return details
        
        # Extract bandwidth
        bandwidth_patterns = [
            r'(\d+[MG]bit)\s+unmetered',
            r'(\d+)\s*TB\s+(?:Monthly Transfer|Bandwidth)?',
            r'Unmetered\s+(?:Bandwidth|Transfer)'
        ]
        for pattern in bandwidth_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'unmetered' in text.lower():
                    details['bandwidth'] = f"{match.group(1) if match.lastindex else 'Unmetered'} unmetered"
                else:
                    details['bandwidth'] = match.group(0)
                break
        
        # Extract port speed
        port_match = re.search(r'(\d+[MG]bit)\s+Port', text, re.IGNORECASE)
        if port_match:
            details['port_speed'] = port_match.group(1)
        
        # Extract IPv4
        ipv4_match = re.search(r'(\d+)\s+usable\s+IPv4', text, re.IGNORECASE)
        if ipv4_match:
            details['ipv4_addresses'] = f"{ipv4_match.group(1)} usable IPv4"
        
        # Extract IPv6
        ipv6_match = re.search(r'/(\d+)\s+IPv6', text, re.IGNORECASE)
        if ipv6_match:
            details['ipv6_addresses'] = f"/{ipv6_match.group(1)} IPv6 Block"
        
        # Check features
        if re.search(r'Instant\s+Deployment', text, re.IGNORECASE):
            details['instant_deployment'] = True
        if re.search(r'FREE\s+Setup', text, re.IGNORECASE):
            details['free_setup'] = True
        
        # Extract location
        locations = ['Dallas', 'Charlotte', 'Lenoir', 'Kansas', 'Phoenix', 'Denver', 'Los Angeles', 'New York']
        for loc in locations:
            if loc.lower() in text.lower():
                details['location'] = loc
                break
        
        # Additional features
        features = []
        if re.search(r'DDoS', text, re.IGNORECASE):
            features.append('DDoS Protection')
        if re.search(r'IPMI', text, re.IGNORECASE):
            features.append('IPMI')
        if re.search(r'Customizable', text, re.IGNORECASE):
            features.append('Customizable')
        
        details['additional_features'] = features
        return details
    
    def parse_server_row(self, row, category, debug=False):
        """Parse a table row containing server information"""
        cells = row.find_all(['td'])
        
        # Skip if this is a header row or has too few cells
        if len(cells) < 5 or row.find('th'):
            return None
        
        if debug:
            print(f"\n  DEBUG: Row has {len(cells)} cells")
            for i, cell in enumerate(cells):
                text = self.extract_text_clean(cell)[:100]
                print(f"    Cell {i}: {text}")
        
        server = {
            'category': category,
            'processor': {'name': '', 'speed': '', 'cores': '', 'threads': ''},
            'ram': '',
            'storage': '',
            'bandwidth': '',
            'port_speed': '',
            'ipv4_addresses': '',
            'ipv6_addresses': '',
            'location': '',
            'price': '',
            'instant_deployment': False,
            'free_setup': False,
            'additional_features': []
        }
        
        # CORRECT COLUMN MAPPING (0-indexed):
        # Cell 0: Image (skip)
        # Cell 1: Processor
        # Cell 2: RAM
        # Cell 3: Storage
        # Cell 4: Included (bandwidth, IPs, etc.)
        # Cell 5: Price button
        
        # Parse processor (cell 1)
        if len(cells) > 1:
            processor_text = self.extract_text_clean(cells[1])
            if processor_text:
                lines = [line.strip() for line in processor_text.split('\n') if line.strip()]
                if lines:
                    server['processor']['name'] = lines[0]
                
                full_text = ' '.join(lines)
                
                # Extract GHz
                ghz_match = re.search(r'(\d+\.?\d*)\s*Ghz', full_text, re.IGNORECASE)
                if ghz_match:
                    server['processor']['speed'] = f"{ghz_match.group(1)}GHz"
                
                # Extract cores and threads
                cores_match = re.search(r'(\d+)\s+Cores?\s*/\s*(\d+)\s+threads?', full_text, re.IGNORECASE)
                if cores_match:
                    server['processor']['cores'] = cores_match.group(1)
                    server['processor']['threads'] = cores_match.group(2)
                else:
                    cores_match = re.search(r'(\d+)\s+Cores?', full_text, re.IGNORECASE)
                    if cores_match:
                        server['processor']['cores'] = cores_match.group(1)
        
        # Parse RAM (cell 2)
        if len(cells) > 2:
            server['ram'] = self.extract_text_clean(cells[2])
        
        # Parse storage (cell 3)
        if len(cells) > 3:
            server['storage'] = self.extract_text_clean(cells[3])
        
        # Parse included column (cell 4)
        if len(cells) > 4:
            included_text = self.extract_text_clean(cells[4])
            included_details = self.parse_included_column(included_text)
            
            server['bandwidth'] = included_details['bandwidth']
            server['port_speed'] = included_details['port_speed']
            server['ipv4_addresses'] = included_details['ipv4_addresses']
            server['ipv6_addresses'] = included_details['ipv6_addresses']
            server['instant_deployment'] = included_details['instant_deployment']
            server['free_setup'] = included_details['free_setup']
            server['location'] = included_details['location']
            server['additional_features'] = included_details['additional_features']
        
        # Parse price (cell 5)
        if len(cells) > 5:
            price_cell = cells[5]
            button = price_cell.find(['a', 'button'])
            if button:
                button_text = self.extract_text_clean(button)
                server['price'] = self.parse_price(button_text)
            else:
                cell_text = self.extract_text_clean(price_cell)
                server['price'] = self.parse_price(cell_text)
        
        # Only return if we have essential data
        if server['processor']['name'] or server['ram'] or server['storage']:
            return server
        
        return None
    
    def extract_server_details(self, html, category):
        """Extract server details from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        servers = []
        
        # Look for section headers
        section_headers = soup.find_all(['h2', 'h3', 'h4'], 
                                       string=re.compile(r'AMD|Intel|Opteron|Xeon|EPYC|Ryzen|Core Series', re.IGNORECASE))
        
        debug_first = True  # Debug first row of first table
        
        for header in section_headers:
            section_name = self.extract_text_clean(header)
            
            # Skip the main "Instant Activation" or "Custom Servers" headers
            if section_name in ['Instant Activation Preconfigured Servers', 'Custom Servers']:
                continue
            
            current = header
            table = None
            
            for sibling in header.find_next_siblings(limit=10):
                if sibling.name == 'table':
                    table = sibling
                    break
                table = sibling.find('table')
                if table:
                    break
            
            if table:
                rows = table.find_all('tr')
                print(f"  Processing section '{section_name}' with {len(rows)} rows")
                
                for row in rows:
                    server_data = self.parse_server_row(row, f"{category} - {section_name}", debug=debug_first)
                    debug_first = False  # Only debug first row
                    if server_data:
                        servers.append(server_data)
        
        # Also parse all tables if no sections found
        if not servers:
            print(f"  No section headers found, parsing all tables...")
            tables = soup.find_all('table')
            print(f"  Found {len(tables)} tables")
            
            for idx, table in enumerate(tables):
                rows = table.find_all('tr')
                print(f"  Table {idx + 1}: {len(rows)} rows")
                
                for row in rows:
                    server_data = self.parse_server_row(row, category, debug=(idx == 0 and debug_first))
                    debug_first = False
                    if server_data:
                        servers.append(server_data)
        
        return servers
    
    def scrape_all(self):
        """Scrape all URLs and compile results"""
        all_servers = []
        
        for url in self.urls:
            print(f"\nScraping {url}...")
            
            category = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
            if category.lower() == 'dedicated':
                category = 'Dedicated Servers'
            
            html = self.fetch_page(url)
            if html:
                servers = self.extract_server_details(html, category)
                print(f"✓ Found {len(servers)} servers in {category}")
                all_servers.extend(servers)
            else:
                print(f"✗ Failed to fetch {category}")
            
            time.sleep(2)
        
        return all_servers
    
    def save_to_json(self, data, filename='nocix_servers.json'):
        """Save scraped data to JSON file"""
        output = {
            'scraped_at': datetime.now().isoformat(),
            'total_servers': len(data),
            'servers': data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print(f"Data saved to {filename}")
        print(f"Total servers scraped: {len(data)}")
        print(f"{'='*80}")
        return filename

def main():
    scraper = NOCIXScraper()
    servers = scraper.scrape_all()
    
    if servers:
        scraper.save_to_json(servers)
        
        # Print sample data
        print("\nSample server data:")
        print("="*80)
        if servers:
            sample = servers[0]
            print(json.dumps(sample, indent=2))
            
            # Show statistics
            print("\n" + "="*80)
            print("Field coverage statistics:")
            print("="*80)
            fields_to_check = [
                ('processor.name', lambda s: s['processor']['name']),
                ('ram', lambda s: s['ram']),
                ('storage', lambda s: s['storage']),
                ('bandwidth', lambda s: s['bandwidth']),
                ('port_speed', lambda s: s['port_speed']),
                ('ipv4_addresses', lambda s: s['ipv4_addresses']),
                ('ipv6_addresses', lambda s: s['ipv6_addresses']),
                ('instant_deployment', lambda s: s['instant_deployment']),
                ('free_setup', lambda s: s['free_setup']),
                ('price', lambda s: s['price'])
            ]
            for field_name, getter in fields_to_check:
                count = sum(1 for s in servers if getter(s))
                percentage = (count / len(servers) * 100) if servers else 0
                print(f"{field_name:20s}: {count:3d}/{len(servers):3d} ({percentage:5.1f}%)")
    else:
        print("\n⚠ No servers found. Please check the website structure.")

if __name__ == "__main__":
    main()