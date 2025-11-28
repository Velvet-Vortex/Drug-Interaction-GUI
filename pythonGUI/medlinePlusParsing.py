import requests
from bs4 import BeautifulSoup
import re
import sys
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple

class DrugDatabase:
    """Manages local cache of drug data in JSON format."""
    
    def __init__(self, db_file='drug_database.json'):
        self.db_file = db_file
        self.data = self._load_database()
    
    def _load_database(self) -> Dict:
        """Load existing database or create new one."""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"⚠ Warning: Could not parse {self.db_file}, creating new database")
                return {'drugs': {}, 'metadata': {'last_updated': None}}
        return {'drugs': {}, 'metadata': {'last_updated': None}}
    
    def save_database(self):
        """Save database to JSON file."""
        self.data['metadata']['last_updated'] = datetime.now().isoformat()
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        print(f"✓ Database saved to {self.db_file}")
    
    def get_drug(self, drug_name: str) -> Optional[Dict]:
        """Retrieve drug data from cache."""
        return self.data['drugs'].get(drug_name.lower())
    
    def add_drug(self, drug_name: str, drug_data: Dict):
        """Add or update drug data in cache."""
        self.data['drugs'][drug_name.lower()] = {
            **drug_data,
            'cached_at': datetime.now().isoformat()
        }
    
    def list_cached_drugs(self) -> List[str]:
        """Get list of all cached drug names."""
        return list(self.data['drugs'].keys())
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        return {
            'total_drugs': len(self.data['drugs']),
            'last_updated': self.data['metadata']['last_updated']
        }


class MedlinePlusScraper:
    """Scrapes drug information from MedlinePlus."""
    
    def __init__(self, use_cache=True, cache_file='drug_database.json'):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.use_cache = use_cache
        self.db = DrugDatabase(cache_file) if use_cache else None
        
        # MedlinePlus URL patterns (structure knowledge)
        self.url_patterns = {
            'index': 'https://medlineplus.gov/druginfo/drug_{letter}a.html',
            'ahfs_index': 'https://medlineplus.gov/druginfo/meds/index.html',
            'base': 'https://medlineplus.gov'
        }
    
    def find_drug_page(self, drug_name: str) -> Optional[Tuple[str, str]]:
        """
        Find the MedlinePlus drug information page URL.
        
        Args:
            drug_name: Name of the drug to search for
        
        Returns:
            Tuple of (title, url) or None if not found
        """
        # Check cache first
        if self.use_cache:
            cached = self.db.get_drug(drug_name)
            if cached:
                print(f"✓ Found '{drug_name}' in cache")
                return (cached['title'], cached['url'])
        
        print(f"Searching for '{drug_name}' on MedlinePlus...")
        
        try:
            first_letter = drug_name[0].upper()
        except IndexError:
            print("Error: Drug name cannot be empty.")
            return None
        
        # Try letter-based index first
        index_url = self.url_patterns['index'].format(letter=first_letter)
        print(f"Checking drug index: {index_url}")
        
        result = self._search_index_page(index_url, drug_name)
        
        # Fallback to comprehensive AHFS index
        if not result:
            print(f"Not found in letter index, checking AHFS comprehensive index...")
            result = self._search_index_page(self.url_patterns['ahfs_index'], drug_name)
        
        if result:
            print(f"✓ Found: {result[0]}")
        else:
            print(f"✗ Drug '{drug_name}' not found in index")
        
        return result
    
    def _search_index_page(self, index_url: str, drug_name: str) -> Optional[Tuple[str, str]]:
        """Search a specific index page for the drug."""
        try:
            response = requests.get(index_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            drug_name_lower = drug_name.lower()
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                link_text = link.get_text(strip=True).lower()
                
                # Check if this is a drug page link
                if './meds/' in href or '/druginfo/meds/' in href:
                    # Check if the link text matches our drug name
                    if drug_name_lower in link_text or link_text in drug_name_lower:
                        # Construct the full URL
                        full_url = self._construct_full_url(href)
                        title = link.get_text(strip=True)
                        return (title, full_url)
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Error accessing index: {e}")
            return None
    
    def _construct_full_url(self, href: str) -> str:
        """Construct full URL from relative path."""
        if href.startswith('http'):
            return href
        elif href.startswith('./meds/'):
            return f"{self.url_patterns['base']}/druginfo/meds/{href[7:]}"
        elif href.startswith('/druginfo/meds/'):
            return f"{self.url_patterns['base']}{href}"
        elif href.startswith('/'):
            return f"{self.url_patterns['base']}{href}"
        else:
            return f"{self.url_patterns['base']}/druginfo/meds/{href}"
    
    def extract_side_effects(self, url: str) -> Optional[Dict]:
        """
        Fetch drug page and extract side effect information.
        
        Args:
            url: URL of the MedlinePlus drug page
        
        Returns:
            Dictionary with categorized side effects and metadata
        """
        print(f"\nFetching drug information page...")
        
        try:
            response = requests.get(url, timeout=10, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            side_effects_data = {
                'common': [],
                'serious': [],
                'other': [],
                'metadata': {
                    'sections_found': 0,
                    'extraction_date': datetime.now().isoformat()
                }
            }
            
            print("\nSearching for side effects information...")
            
            # Keywords for section detection
            section_keywords = [
                'side effect', 'effects of this medication', 'what side effects',
                'adverse effect', 'unwanted effect'
            ]
            
            serious_keywords = [
                'serious', 'severe', 'emergency', 'call your doctor',
                'seek help', 'get emergency', 'tell your doctor immediately'
            ]
            
            common_keywords = [
                'common', 'minor', 'less serious', 'may cause', 'some side effects'
            ]
            
            for heading in soup.select('h2, h3, h4'):
                heading_text = heading.get_text().strip()
                heading_text_lower = heading_text.lower()
                
                # Check if this is a side effects section
                if any(keyword in heading_text_lower for keyword in section_keywords):
                    side_effects_data['metadata']['sections_found'] += 1
                    print(f"  ✓ Found section: {heading_text}")
                    
                    # Determine category
                    if any(kw in heading_text_lower for kw in serious_keywords):
                        category = 'serious'
                    elif any(kw in heading_text_lower for kw in common_keywords):
                        category = 'common'
                    else:
                        category = 'other'
                    
                    # Extract content after this heading
                    current_elem = heading.find_next_sibling()
                    
                    while current_elem and current_elem.name not in ['h2', 'h3', 'h4']:
                        if current_elem.name == 'p':
                            text = current_elem.get_text(strip=True)
                            if text and len(text) > 15:
                                side_effects_data[category].append(text)
                        
                        elif current_elem.name in ['ul', 'ol']:
                            for li in current_elem.find_all('li', recursive=False):
                                text = li.get_text(strip=True)
                                if text:
                                    side_effects_data[category].append(text)
                        
                        current_elem = current_elem.find_next_sibling()
            
            total_items = sum(len(side_effects_data[k]) for k in ['common', 'serious', 'other'])
            print(f"  ✓ Extracted {total_items} side effect entries from {side_effects_data['metadata']['sections_found']} sections")
            
            return side_effects_data
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Error fetching page: {e}")
            return None
        except Exception as e:
            print(f"  ✗ Error parsing page: {e}")
            return None
    
    def get_drug_info(self, drug_name: str, force_refresh=False) -> Optional[Dict]:
        """
        Get complete drug information (combines search and extraction).
        
        Args:
            drug_name: Name of the drug
            force_refresh: If True, bypass cache and fetch fresh data
        
        Returns:
            Complete drug information dictionary
        """
        # Check cache unless force refresh
        if self.use_cache and not force_refresh:
            cached = self.db.get_drug(drug_name)
            if cached and 'side_effects' in cached:
                print(f"✓ Using cached data for '{drug_name}'")
                return cached
        
        # Find drug page
        result = self.find_drug_page(drug_name)
        if not result:
            return None
        
        title, url = result
        
        # Extract side effects
        print(f"\n{'='*70}")
        print("EXTRACTING SIDE EFFECTS")
        print(f"{'='*70}")
        
        side_effects = self.extract_side_effects(url)
        if not side_effects:
            return None
        
        # Build complete drug info
        drug_info = {
            'title': title,
            'url': url,
            'search_term': drug_name,
            'side_effects': side_effects
        }
        
        # Cache the result
        if self.use_cache:
            self.db.add_drug(drug_name, drug_info)
            self.db.save_database()
        
        return drug_info


def print_side_effects(drug_info: Dict):
    """Print side effects in a formatted way."""
    print("\n" + "="*70)
    print(f"SIDE EFFECTS FOR: {drug_info['title'].upper()}")
    print("="*70)
    
    side_effects = drug_info['side_effects']
    
    has_effects = any(len(side_effects[key]) > 0 for key in ['common', 'serious', 'other'])
    
    if not has_effects:
        print("\n❌ No side effects information found.")
        print(f"For complete information, visit: {drug_info['url']}")
        return
    
    if side_effects['serious']:
        print("\n🔴 SERIOUS SIDE EFFECTS - CALL DOCTOR IMMEDIATELY:")
        print("-" * 70)
        for effect in side_effects['serious']:
            print(f"• {effect}")
    
    if side_effects['common']:
        print("\n🔵 COMMON/MINOR SIDE EFFECTS:")
        print("-" * 70)
        for effect in side_effects['common']:
            print(f"• {effect}")
    
    if side_effects['other']:
        print("\n⚪ OTHER SIDE EFFECTS:")
        print("-" * 70)
        for effect in side_effects['other']:
            print(f"• {effect}")
    
    print("\n" + "="*70)
    print(f"Source: {drug_info['url']}")
    if 'cached_at' in drug_info:
        print(f"Cached: {drug_info['cached_at']}")


def save_json(drug_info: Dict, filename: str = None):
    """Save drug info to individual JSON file."""
    if not filename:
        safe_name = re.sub(r'[^\w\s-]', '', drug_info['search_term'].lower())
        safe_name = re.sub(r'[\s]+', '_', safe_name)
        filename = f"{safe_name}_info.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(drug_info, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Data saved to: {filename}")
    return filename


# Helper function to generate standardized array
def get_formatted_output_array(drug_info: Dict) -> List:
    """
    Format the drug info into the standardized array structure:
    [0] Drug 1, [1] Drug 2, [2] Severity, [3] URL, [4] Description, [5] Extras
    """
    if not drug_info:
        return ["Unknown", "N/A", "N/A", "N/A", "No data found", {}]
        
    side_effects = drug_info.get('side_effects', {})
    
    # Consolidate description text for [4]
    desc_parts = []
    if side_effects.get('serious'):
        # Take top 3 serious effects
        top_serious = side_effects['serious'][:3]
        desc_parts.append(f"SERIOUS: {'; '.join(top_serious)}")
        
    if side_effects.get('common'):
        # Take top 3 common effects
        top_common = side_effects['common'][:3]
        desc_parts.append(f"COMMON: {'; '.join(top_common)}")
        
    description = " | ".join(desc_parts) if desc_parts else "No detailed side effects extracted."
    
    # [5] Extras - Everything else as a dictionary
    extras = {
        'all_side_effects': side_effects,
        'cached_at': drug_info.get('cached_at'),
        'search_term': drug_info.get('search_term')
    }
    
    # Create the array [0] Drug 1, [1] Drug 2, [2] Severity, [3] URL, [4] Description, [5] Extras
    output_array = [
        drug_info.get('title', 'Unknown'),  # [0] Drug 1
        "N/A",                              # [1] Drug 2 (Not applicable for single drug)
        "N/A",                              # [2] Severity (Not applicable for single drug)
        drug_info.get('url', 'N/A'),        # [3] URL
        description,                        # [4] Description
        extras                              # [5] Extras (Full dictionary)
    ]
    
    return output_array


def main():
    """Main function with enhanced features."""
    
    print("="*70)
    print("MEDLINEPLUS DRUG INFORMATION EXTRACTOR v2.0")
    print("Features: JSON export, caching, batch processing")
    print("="*70)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--list':
            # List cached drugs
            scraper = MedlinePlusScraper()
            drugs = scraper.db.list_cached_drugs()
            stats = scraper.db.get_stats()
            print(f"\n📊 Database Stats:")
            print(f"   Total drugs: {stats['total_drugs']}")
            print(f"   Last updated: {stats['last_updated']}")
            print(f"\n📚 Cached drugs:")
            for drug in sorted(drugs):
                print(f"   • {drug}")
            return
        
        elif sys.argv[1] == '--stats':
            # Show stats only
            scraper = MedlinePlusScraper()
            stats = scraper.db.get_stats()
            print(f"\n📊 Database Statistics:")
            print(f"   Total drugs cached: {stats['total_drugs']}")
            print(f"   Last updated: {stats['last_updated']}")
            print(f"   Database file: {scraper.db.db_file}")
            return
        
        else:
            drug_name = ' '.join(sys.argv[1:])
    else:
        drug_name = input("\nEnter drug name (e.g., Aspirin, Ibuprofen, Lisinopril): ").strip()
    
    if not drug_name:
        print("No drug name entered. Exiting.")
        return
    
    print()
    
    # Initialize scraper
    scraper = MedlinePlusScraper(use_cache=True)
    
    # Get drug info
    drug_info = scraper.get_drug_info(drug_name)
    
    if not drug_info:
        print(f"\n❌ Could not find '{drug_name}' on MedlinePlus")
        print("\nTroubleshooting:")
        print("  • Check spelling")
        print("  • Try the generic name (e.g., 'acetaminophen' not 'Tylenol')")
        print("  • Try just the drug name without dosage")
        print("  • Visit https://medlineplus.gov/druginformation.html to verify")
        
        # Print empty array for I/O consistency if not found
        print("\n" + "=" * 70)
        print("FINAL OUTPUT ARRAY")
        print("=" * 70)
        # [0] Drug 1, [1] Drug 2, [2] Severity, [3] URL, [4] Description, [5] Extras
        print([drug_name, "N/A", "N/A", "N/A", "Not Found", {}])
        return
    
    # Display results
    print_side_effects(drug_info)
    
    # OUTPUT: Print the formalized array for I/O
    print("\n" + "=" * 70)
    print("FINAL OUTPUT ARRAY")
    print("=" * 70)
    # [0] Drug 1, [1] Drug 2, [2] Severity, [3] URL, [4] Description, [5] Extras
    output_array = get_formatted_output_array(drug_info)
    print(output_array)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn unhandled error occurred: {e}")
        import traceback
        traceback.print_exc()

