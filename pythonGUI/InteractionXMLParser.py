#ElementTree reads XML structure and parses <url> and <loc> tags
import xml.etree.ElementTree as ET
#RegularExpressions removes Numeric ID's
import re
#URLLibrary extracts the path from URLs
from urllib.parse import urlparse
#Sys lets us access command line arguments
import sys
#OS can join the file paths for any OS
import os

from interactionScraperHTML import DrugInteractionScraper

#Gets the sitemap for the Interaction Website
#Makes a library of searchable URLS
class DrugInteractionParser:
    def __init__(self, xml_file_path):
        
#Get the directory, speeds up the searches
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
#Get the absolute path to the XML files
        self.xml_file_path = os.path.join(script_dir, xml_file_path)
#Empty;ost to store each of the URLs
        self.interactions = []
        self.parse_xml()

#Pulls all of the URLs out of the XML file
    def parse_xml(self):

#Removes the root to each URL then saves it
        try:
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()

            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
#Moves the URLs to the List
            for url in root.findall('ns:url/ns:loc', namespace):
                self.interactions.append(url.text)
            
            print(f"Loaded {len(self.interactions)} drug interaction entries from XML file.")

#Exception handling for parsing the filepath
        except ET.ParseError as e:
            print(f"Error parsing XML file: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print(f"Error: File '{self.xml_file_path}' not found.")
            sys.exit(1)

#Make drug names lowercase and turn ' ' to hyphens
#Returns the drug name as a string
    def normalize_drug_name(self, drug_name):
        return drug_name.lower().strip().replace(' ', '-')

#Removes the drug names from each URL
#Returns a tuple for easy parsing
    def extract_drugs_from_url(self, url):
        try:
#Extract the path from URL
            path = urlparse(url).path
            
#Remove /drug-interactions/ and .html
            path = path.replace('/drug-interactions/', '').replace('.html', '')
            
#-with- separates two drugs in the URLs
#Remove that and split to a list
            if '-with-' in path:
                parts = path.split('-with-')
                drug1_part = parts[0]
                drug2_part = parts[1] if len(parts) > 1 else ''
                
#Removes the numeric ID applied to each
                drug1 = re.sub(r'-\d+(-\d+)*$', '', drug1_part)
                drug2 = re.sub(r'-\d+(-\d+)*$', '', drug2_part)

#Exception handling for parsing
                return (drug1, drug2)
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
        
        return None

#Searches the two drugs to find any listed interaction
#Returns URL if exists, nothing if not
    def check_interaction(self, drug1, drug2):
#Normalize both drug inputs from user
        drug1_norm = self.normalize_drug_name(drug1)
        drug2_norm = self.normalize_drug_name(drug2)

#Set a list for the URLs
        matching_urls = []

#Loop through URL Directory to make the search O(1) time
        for url in self.interactions:
            drugs = self.extract_drugs_from_url(url)
            
            if drugs:
                url_drug1, url_drug2 = drugs
                
#Reorder drugs then try search again
                if ((drug1_norm == url_drug1 and drug2_norm == url_drug2) or
                    (drug2_norm == url_drug1 and drug1_norm == url_drug2)):
                    matching_urls.append(url)
        
        return matching_urls

#Searches interactions that do exist from the HTM results
#From the list, checks if the interactions were found
    def search_drug_interactions(self, drug1, drug2):

        #Series of print statements to check interactons
        print(f"\nSearching for interactions between '{drug1}' and '{drug2}'...")
        print("-" * 70)

#set interaction to a string
        results = self.check_interaction(drug1, drug2)

#Confirm results for the user
        if results:
            print(f"\n INTERACTION FOUND: {len(results)} interaction(s) detected!\n")
            for i, url in enumerate(results, 1):
                print(f"{i}. {url}")
            return results
        else:
            print(f"\n No interaction found between '{drug1}' and '{drug2}'.")
            print("Note: This doesn't guarantee safety - always consult a healthcare professional.")
            return []

#main() to run the drug intraction checks
def main():
    
    # Manually set the XML file name
    xml_file = "drug-interactions.xml" 
    
    # Manually set the two drugs
    drug1 = "acebutolol"
    drug2 = "taurine"
    
    # No command-line argument check is needed
    
    # Create parser and check interaction
    parser = DrugInteractionParser(xml_file)
    results = parser.search_drug_interactions(drug1, drug2)

    if results and len(results) > 0:

#Use the first URL found
        url = results[0]
# Create scraper instance and get detailed info
        scraper = DrugInteractionScraper(url)
        data = scraper.scrape_all()
        if data:
            scraper.print_summary()
            scraper.save_to_json('interaction_data.json')
            print("\n Detailed interaction data saved successfully!")

        else:
            print("\n Could not scrape detailed information from URL")



#This is the code we'll use when running this program
#Right now it is set to Hard Code each drug into the system
    """
    #Check command line arguments
    if len(sys.argv) != 4:
        print("Usage: python drug_interaction_parser.py <xml_file> <drug1> <drug2>")
        print("\nExample:")
        print("  python drug_interaction_parser.py interactions.xml \"warfarin\" \"aspirin\"")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    drug1 = sys.argv[2]
    drug2 = sys.argv[3]
    
    #Create parser and check interaction
    parser = DrugInteractionParser(xml_file)
    parser.search_drug_interactions(drug1, drug2)
"""

if __name__ == "__main__":
    main()
