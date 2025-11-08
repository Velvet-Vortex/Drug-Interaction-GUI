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

#Sets the URL variable
#Declares the list and 
        self.url = url
        self.html_content = None
        self.soup = None
        self.interaction_data = {}
    
#THis mimics a windows page in order to fetch the HTML
    def fetch_page(self):
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
            print(f" Successfully fetched: {self.url}")
            return True
#Exception handling
        except requests.RequestException as e:
            print(f" Error fetching URL: {e}")
            return False

#Parses the main element header for the names of the drugs
    def extract_drug_names(self):

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
            
#Alternative: extract from breadcrumb or meta tags
            breadcrumb = self.soup.find('nav', class_='breadcrumb')
            if breadcrumb:
                items = breadcrumb.find_all('li')
                if len(items) >= 2:
                    self.interaction_data['drug1'] = items[-2].get_text(strip=True)
                    self.interaction_data['drug2'] = items[-1].get_text(strip=True)
                    return True
#Exception for if drug names aren't found
        except Exception as e:
            print(f"Warning: Could not extract drug names: {e}")
        
        return False

#Tests the listed danger/safetly of the interaction
    def extract_interaction_severity(self):

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
                    # Extract severity level
                    if 'major' in severity_text.lower():
                        self.interaction_data['severity'] = 'Major'
                    elif 'moderate' in severity_text.lower():
                        self.interaction_data['severity'] = 'Moderate'
                    elif 'minor' in severity_text.lower():
                        self.interaction_data['severity'] = 'Minor'
                    else:
                        self.interaction_data['severity'] = severity_text
                    return True
            
#XML uses premade alert boxes that give other warnings
#Parses data for additional alert boxes or warnings and saves the body text
            alert = self.soup.find('div', class_=['alert', 'warning', 'ddc-alert'])
            if alert:
                alert_text = alert.get_text(strip=True)
                for level in ['Major', 'Moderate', 'Minor']:
                    if level.lower() in alert_text.lower():
                        self.interaction_data['severity'] = level
                        return True
#If no additional warnings then handle the exception
        except Exception as e:
            print(f"Warning: Could not extract severity: {e}")
        
        return False
#This parses the <h1> block for how the drugs interact
    def extract_interaction_description(self):

#set a list to save that data
        try:
            descriptions = []
            
#Extract the description paragraphs
            content_sections = self.soup.find_all(['div', 'section'], class_=re.compile(r'interaction|content|description'))
            
            for section in content_sections:
                paragraphs = section.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
#Filter non-content paragraphs
                    if len(text) > 50 and not text.startswith(('Home', 'Navigate', 'Copyright')):
                        descriptions.append(text)
            
            if descriptions:
                self.interaction_data['description'] = descriptions
                return True
            
            #If data isn't found get all paragraphs from main content
            main_content = self.soup.find(['main', 'article', 'div'], {'id': re.compile(r'content|main')})
            if main_content:
                paragraphs = main_content.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50:
                        descriptions.append(text)
                
                if descriptions:
                    self.interaction_data['description'] = descriptions[:3]
                    return True
#If there is still a problem extracting data, handle that exception
        except Exception as e:
            print(f"Warning: Could not extract description: {e}")
        
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
                
                # Extract mechanism of interaction
                mechanism = prof_section.find(text=re.compile(r'mechanism', re.IGNORECASE))
                if mechanism:
                    parent = mechanism.find_parent(['p', 'div'])
                    if parent:
                        info['mechanism'] = parent.get_text(strip=True)
                
#Extract doseage management information
                management = prof_section.find(text=re.compile(r'management|recommendation', re.IGNORECASE))
                if management:
                    parent = management.find_parent(['p', 'div'])
                    if parent:
                        info['management'] = parent.get_text(strip=True)
                
#Save data to array
                if info:
                    self.interaction_data['professional_info'] = info
                    return True
                    
#If there are no expert specific terms, handle it
        except Exception as e:
            print(f"Warning: Could not extract professional info: {e}")
        
        return False

#Extracts the links and data sources in the html file
    def extract_references(self):

#Save them to a list
        try:
            references = []
            
#Find a reference section
            ref_section = self.soup.find(['div', 'section'], class_=re.compile(r'reference|citation'))
            
            if ref_section:
                links = ref_section.find_all('a')
                for link in links:
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    if href and text:
                        references.append({'text': text, 'url': href})
            
#Save references to a list
            if references:
                self.interaction_data['references'] = references
                return True
               
#No references, handle the exception 
        except Exception as e:
            print(f"Warning: Could not extract references: {e}")
        
        return False

#With all the data in the lists, scrape the data
#Returns a dictionary with all the key data
    def scrape_all(self):

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

#Run the code and test every method/function
def main():
    #This sets the drug interaction link
    url = sys.argv[1]
    #This file will be overwritten each time for JavaScript integration
    output_file = 'interaction_data.json'
    
    #Just creates scraper instance and runs extraction directly
    scraper = DrugInteractionScraper(url)
    data = scraper.scrape_all()
    
    if data:
        scraper.print_summary()
        scraper.save_to_json(output_file)
    else:
        print("Failed to scrape interaction data.")
        sys.exit(1)
"""
#Prints the output of each run of the code    
    if len(sys.argv) < 2:
        print("Usage: python drug_interaction_scraper.py <url> [output_file.json]")
        print("\nExample:")
        print("  python drug_interaction_scraper.py \"https://www.drugs.com/drug-interactions/warfarin-with-aspirin-1247-0-198-439.html\"")
        print("  python drug_interaction_scraper.py \"<url>\" output.json")
        sys.exit(1)
#Declares a list for the output
    url = sys.argv[1]
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
"""

if __name__ == "__main__":
    main()
