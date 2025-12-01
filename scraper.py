import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

class NOCIXScraper:
    def __init__(self):
        self.base_url = "https://www.nocix.net"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
    
    def extract_server_details(self, html, category):
        """Extract server details from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        servers = []
        
        # Look for server cards/blocks - adjust selectors based on actual HTML structure
        server_blocks = soup.find_all(['div', 'article'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['server', 'product', 'plan', 'package', 'card']
        ))
        
        # Also try table rows if servers are in tables
        table_rows = soup.find_all('tr')
        
        for block in server_blocks + table_rows:
            server_data = self.parse_server_block(block, category)
            if server_data and server_data.get('name'):
                servers.append(server_data)
        
        # Remove duplicates based on name
        seen = set()
        unique_servers = []
        for server in servers:
            if server['name'] not in seen:
                seen.add(server['name'])
                unique_servers.append(server)
        
        return unique_servers
    
    def parse_server_block(self, block, category):
        """Parse individual server block for details"""
        server = {
            'category': category,
            'name': '',
            'cpu': '',
            'ram': '',
            'storage': '',
            'bandwidth': '',
            'port_speed': '',
            'price': '',
            'ipv4': '',
            'location': '',
            'additional_features': []
        }
        
        text = block.get_text(separator=' ', strip=True)
        
        # Extract name/title
        title_elem = block.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
        if title_elem:
            server['name'] = title_elem.get_text(strip=True)
        
        # Extract CPU info
        cpu_patterns = ['Intel', 'AMD', 'Xeon', 'Core', 'Ryzen', 'EPYC', 'Processor']
        for pattern in cpu_patterns:
            if pattern.lower() in text.lower():
                # Try to extract CPU details
                words = text.split()
                for i, word in enumerate(words):
                    if pattern.lower() in word.lower():
                        cpu_text = ' '.join(words[i:min(i+6, len(words))])
                        if len(cpu_text) > len(server['cpu']):
                            server['cpu'] = cpu_text
                        break
        
        # Extract RAM
        if 'gb' in text.lower() and ('ram' in text.lower() or 'memory' in text.lower()):
            import re
            ram_match = re.search(r'(\d+)\s*GB\s*(DDR\d?)?.*?(RAM|Memory)', text, re.IGNORECASE)
            if ram_match:
                server['ram'] = ram_match.group(0)
        
        # Extract Storage
        storage_patterns = ['TB', 'GB', 'SSD', 'HDD', 'NVMe', 'SATA']
        for pattern in storage_patterns:
            if pattern.lower() in text.lower():
                import re
                storage_match = re.search(r'(\d+)\s*(x\s*)?(\d+)?\s*(TB|GB)\s*(SSD|HDD|NVMe|SATA)?', text, re.IGNORECASE)
                if storage_match:
                    server['storage'] = storage_match.group(0)
                    break
        
        # Extract Bandwidth
        import re
        bandwidth_match = re.search(r'(\d+)\s*(TB|GB|Unmetered|Unlimited).*?(Bandwidth|Transfer)', text, re.IGNORECASE)
        if bandwidth_match:
            server['bandwidth'] = bandwidth_match.group(0)
        
        # Extract Port Speed
        port_match = re.search(r'(\d+)\s*(Gbps|Mbps|Gbit)', text, re.IGNORECASE)
        if port_match:
            server['port_speed'] = port_match.group(0)
        
        # Extract Price
        price_match = re.search(r'\$(\d+(?:\.\d{2})?)\s*(?:/mo|per month|monthly)?', text, re.IGNORECASE)
        if price_match:
            server['price'] = price_match.group(0)
        
        # Extract IPv4
        ipv4_match = re.search(r'(\d+)\s*(?:x\s*)?IPv4', text, re.IGNORECASE)
        if ipv4_match:
            server['ipv4'] = ipv4_match.group(0)
        
        # Extract Location
        locations = ['Dallas', 'Charlotte', 'Lenoir', 'Kansas', 'Phoenix', 'Denver']
        for loc in locations:
            if loc.lower() in text.lower():
                server['location'] = loc
                break
        
        # Extract additional features
        features = []
        feature_keywords = ['DDoS', 'IPMI', 'Remote', 'Backup', 'Setup', 'Free', 'Instant']
        for keyword in feature_keywords:
            if keyword.lower() in text.lower():
                features.append(keyword)
        
        server['additional_features'] = features
        
        return server
    
    def scrape_all(self):
        """Scrape all URLs and compile results"""
        all_servers = []
        
        for url in self.urls:
            print(f"Scraping {url}...")
            
            # Extract category from URL
            category = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
            
            html = self.fetch_page(url)
            if html:
                servers = self.extract_server_details(html, category)
                print(f"Found {len(servers)} servers in {category}")
                all_servers.extend(servers)
            
            # Be respectful - add delay between requests
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
        
        print(f"Data saved to {filename}")
        return filename

def main():
    scraper = NOCIXScraper()
    servers = scraper.scrape_all()
    scraper.save_to_json(servers)
    print(f"\nTotal servers scraped: {len(servers)}")

if __name__ == "__main__":
    main()