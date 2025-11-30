#Requests allows you to call HTML files as though you were a windows
import requests
#BeautifulSoup parses the raw HTML
#Makes a navigatable tree structure to extract data
from bs4 import BeautifulSoup
#System provides access to command line arguments
import sys
#JSON allows to save extracted data to a JSON files
#Needs to be edited and returned as series of strings?
import json
#RegEx performs string parsing for data
import re

#Initializes Scraper Object and sets the HTML from the other program
class DrugInteractionScraper:
    def __init__(self, url):
        """
        Initialize the scraper with a drugs.com interaction URL.
        """
        #Sets the URL variable
        #Declares the list and 
        self.url = url
        self.html_content = None
        self.soup = None
        self.interaction_data = {}
    
    #THis mimics a windows page in order to fetch the HTML
    def fetch_page(self):
        """Fetch the HTML content from the URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            #This fetches the raw HTML data and saves it
            response = requests.get(self.url, headers=headers, timeout=10)
            
            #This sets a time request that will eventually time out
            response.raise_for_status()
            self.html_content = response.text
            
            #Parse the data for a searchable representation of the data
            self.soup = BeautifulSoup(self.html_content, 'html.parser')
            return True
        except requests.RequestException as e:
            #Exception handling
            print(f"✗ Error fetching URL: {e}")
            return False
    
    #Parses the main element header for the names of the drugs
    def extract_drug_names(self):
        """Extract the names of the two drugs being compared."""
        try:
            #Find the page heading
            title = self.soup.find('h1')
            if title:
                title_text = title.get_text(strip=True)
                #Parse "Drug A and Drug B Interactions"
                match = re.search(r'(.+?)\s+and\s+(.+?)\s+(?:Interactions?|Drug)', title_text, re.IGNORECASE)
                #Save the data to a list
                if match:
                    self.interaction_data['drug1'] = match.group(1).strip()
                    self.interaction_data['drug2'] = match.group(2).strip()
                    return True
        except Exception:
            #If drug names aren't found, handle the exception
            pass
        return False
    
    #Tests the listed danger/safetly of the interaction
    def extract_interaction_severity(self):
        """Extract the severity level of the interaction."""
        try:
            #There are three severity indicators (Major, Moderate, Minor)
            #Declare three array zones for data
            severity_patterns = [
                {'class': 'interaction-severity'},
                {'class': 'ddc-status'},
                {'class': 'severity'}
            ]
            
            #Check the header for severity 
            #Use elif block to check for the level
            for pattern in severity_patterns:
                severity_elem = self.soup.find('div', pattern) or self.soup.find('span', pattern)
                if severity_elem:
                    severity_text = severity_elem.get_text(strip=True)
                    if 'major' in severity_text.lower():
                        self.interaction_data['severity'] = 'Major'
                    elif 'moderate' in severity_text.lower():
                        self.interaction_data['severity'] = 'Moderate'
                    elif 'minor' in severity_text.lower():
                        self.interaction_data['severity'] = 'Minor'
                    else:
                        self.interaction_data['severity'] = severity_text
                    return True
        except Exception:
            #If no additional warnings then handle the exception
            pass
        return False
    
    #This parses the <h1> block for how the drugs interact
    def extract_interaction_description(self):
        """Extract the description - looking specifically for drug-drug interaction text."""
        #set a list to save that data
        try:
            descriptions = []
            
            # TOOL 1: Look for the "Interactions between your drugs" section
            # This section contains the actual drug-drug interaction info we want
            section_header = self.soup.find(lambda tag: tag.name in ['h2', 'h3'] and 
                                                        'interactions between your drugs' in tag.get_text().lower())
            
            if section_header:
                # Get the next elements after this header
                current = section_header.find_next_sibling()
                
                # Look for paragraphs that contain the interaction description
                # Skip headers like "acebutolol taurine" or "Applies to:"
                while current and current.name in ['p', 'div', 'h4', 'h5']:
                    if current.name == 'p':
                        text = current.get_text(strip=True)
                        # Skip short headers and "Applies to" lines
                        if len(text) > 100 and not text.startswith('Applies to:'):
                            descriptions.append(text)
                            break # We found our main description
                    current = current.find_next_sibling()
            
            # TOOL 2: Fallback - look for paragraphs after severity indicators
            if not descriptions:
                severity_box = self.soup.find('div', class_=re.compile(r'interaction-severity|ddc-status'))
                if severity_box:
                    # Get paragraphs near the severity box
                    next_elem = severity_box.find_next_sibling()
                    count = 0
                    while next_elem and count < 5: # Look at next 5 siblings
                        if next_elem.name == 'p':
                            text = next_elem.get_text(strip=True)
                            if len(text) > 100 and not text.startswith(('Home', 'Navigate', 'Copyright', 'Applies to:')):
                                descriptions.append(text)
                                break
                        next_elem = next_elem.find_next_sibling()
                        count += 1
            
            # TOOL 3: General search for substantial paragraphs
            if not descriptions:
                all_paragraphs = self.soup.find_all('p')
                for p in all_paragraphs:
                    text = p.get_text(strip=True)
                    # Look for paragraphs that mention both drugs or medication interactions
                    if len(text) > 100 and any(keyword in text.lower() for keyword in 
                                                       ['may add to', 'may decrease', 'may increase', 
                                                        'you may need', 'contact your doctor']):
                        descriptions.append(text)
                        break
            
            if descriptions:
                self.interaction_data['description'] = descriptions
                return True
                        
        except Exception as e:
            print(f"Error extracting description: {e}")
        return False
    
    #This extracts the data particular to healthcare professionals
    def extract_professional_info(self):
        """Extract professional/clinical information if available."""
        try:
            #Parses paragraphs for professional terms
            prof_section = self.soup.find(['div', 'section'], class_=re.compile(r'professional|clinical|mechanism'))
            #If it exists, save it to a variable
            if prof_section:
                info = {}
                # Mechanism
                mech_head = prof_section.find(lambda tag: tag.name in ['h2','h3'] and 'mechanism' in tag.get_text().lower())
                if mech_head:
                    # Simple sibling capture
                    next_p = mech_head.find_next_sibling('p')
                    if next_p:
                        info['mechanism'] = next_p.get_text(strip=True)
                
                # Management
                mgmt_head = prof_section.find(lambda tag: tag.name in ['h2','h3'] and 'management' in tag.get_text().lower())
                #Extract doseage management information
                if mgmt_head:
                    next_p = mgmt_head.find_next_sibling('p')
                    if next_p:
                        info['management'] = next_p.get_text(strip=True)
                
                #Save data to array
                if info:
                    self.interaction_data['professional_info'] = info
                    return True
        except Exception:
            #If there are no expert specific terms, handle it
            pass
        return False
    
    #Extracts the links and data sources in the html file
    def extract_references(self):
        """Extract reference links."""
        #Save them to a list
        try:
            references = []
            #Find a reference section
            ref_section = self.soup.find(['div', 'section'], class_=re.compile(r'reference|citation'))
            if ref_section:
                links = ref_section.find_all('a')
                for link in links:
                    if link.get('href'):
                        references.append({'text': link.get_text(strip=True), 'url': link.get('href')})
            
            #Save references to a list
            if references:
                self.interaction_data['references'] = references
                return True
        except Exception:
            #No references, handle the exception 
            pass
        return False
    
    #With all the data in the lists, scrape the data
    #Returns a dictionary with all the key data
    def scrape_all(self):
        """Scrape all available information."""
        if not self.fetch_page():
            return None
        
        print("\nExtracting interaction data...")
        print("-" * 70)
        
        #Prep a list for all the extracted data
        self.interaction_data['url'] = self.url
        #Extract all components with associated methods
        self.extract_drug_names()
        self.extract_interaction_severity()
        self.extract_interaction_description()
        self.extract_professional_info()
        self.extract_references()
        
        return self.interaction_data
    
    #Prints all the data it Returns
    #Will be removed for return function as part of I/O
    def print_summary(self):
        """Print a formatted summary of the extracted data."""
        if not self.interaction_data:
            print("No data available. Run scrape_all() first.")
            return
        
        #Format the data for a print
        print("\n" + "=" * 70)
        print("DRUG INTERACTION SUMMARY")
        print("=" * 70)
        
        if 'drug1' in self.interaction_data and 'drug2' in self.interaction_data:
            print(f"\n Drugs: {self.interaction_data['drug1']} + {self.interaction_data['drug2']}")
        
        if 'severity' in self.interaction_data:
            severity = self.interaction_data['severity']
            emoji = '🔴' if severity == 'Major' else '🟡' if severity == 'Moderate' else '🟢'
            print(f"{emoji} Severity: {severity}")
        
        if 'description' in self.interaction_data:
            print(f"\n Description:")
            for i, desc in enumerate(self.interaction_data['description'], 1):
                print(f"   {i}. {desc[:200]}..." if len(desc) > 200 else f"   {i}. {desc}")
        
        if 'professional_info' in self.interaction_data:
            print(f"\n Professional Information:")
            for key, value in self.interaction_data['professional_info'].items():
                print(f"   {key.title()}: {value[:150]}..." if len(value) > 150 else f"   {key.title()}: {value}")
        
        if 'references' in self.interaction_data:
            print(f"\n References: {len(self.interaction_data['references'])} found")
        
        print("\n" + "=" * 70)
    
    #Currently saves the data to a JSON file
    #We can start returning strings or could add code to overwrite old JSON file
    #May need to send JSON to server to add cookies which would be difficult
    def save_to_json(self, output_file='interaction_data.json'):
        #Handle the case of no data returning
        if not self.interaction_data:
            print("No data to save.")
            return

        #This block saves all the data to a file named interation_data.json
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.interaction_data, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Data saved to {output_file}")
        except Exception as e:
            print(f"✗ Error saving to JSON: {e}")

#Quick helper for external use.
def get_interaction_description(url):
    """Quick helper for external use."""
    scraper = DrugInteractionScraper(url)
    scraper.scrape_all()
    if 'description' in scraper.interaction_data:
        return scraper.interaction_data['description'][0]
    return None

#Run the code and test every method/function
def main():
    """Main function to run the scraper."""
    
    #Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python drug_interaction_scraper.py <url> [output_file.json]")
        print("\nExample:")
        print('  python drug_interaction_scraper.py "https://www.drugs.com/drug-interactions/warfarin-with-aspirin-1247-0-198-439.html"')
        print('  python drug_interaction_scraper.py "<url>" output.json')
        sys.exit(1)
    
    #This sets the drug interaction link
    url = sys.argv[1]
    #This file will be overwritten each time for JavaScript integration
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'interaction_data.json'
    
    #Create scraper and extract data
    scraper = DrugInteractionScraper(url)
    data = scraper.scrape_all()
    
    if data:
        scraper.print_summary()
        scraper.save_to_json(output_file)
    else:
        print("Failed to scrape interaction data.")
        sys.exit(1)


if __name__ == "__main__":
    main()
