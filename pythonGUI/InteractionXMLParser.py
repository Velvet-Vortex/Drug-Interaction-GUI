# ElementTree reads XML structure and parses <url> and <loc> tags
import xml.etree.ElementTree as ET
# RegularExpressions removes Numeric ID's
import re
# URLLibrary extracts the path from URLs
from urllib.parse import urlparse
# Sys lets us access command line arguments
import sys
# OS can join the file paths for any OS
import os

# Import the scraper to get the detailed data for the array
from InteractionScraperHTML import DrugInteractionScraper

# Gets the sitemap for the Interaction Website
# Makes a library of searchable URLS
class DrugInteractionParser:
    def __init__(self, xml_file_path):
        
        # Get the directory, speeds up the searches
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get the absolute path to the XML files
        self.xml_file_path = os.path.join(script_dir, xml_file_path)
        # Empty list to store each of the URLs
        self.interactions = []
        self.parse_xml()

    # Pulls all of the URLs out of the XML file
    def parse_xml(self):

        # Removes the root to each URL then saves it
        try:
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()

            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Moves the URLs to the List
            for url in root.findall('ns:url/ns:loc', namespace):
                self.interactions.append(url.text)
            
            print(f"Loaded {len(self.interactions)} drug interaction entries from XML file.")

        # Exception handling for parsing the filepath
        except ET.ParseError as e:
            print(f"Error parsing XML file: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print(f"Error: File '{self.xml_file_path}' not found.")
            sys.exit(1)

    # Make drug names lowercase and turn ' ' to hyphens
    # Returns the drug name as a string
    def normalize_drug_name(self, drug_name):
        return drug_name.lower().strip().replace(' ', '-')

    # Removes the drug names from each URL
    # Returns a tuple for easy parsing
    def extract_drugs_from_url(self, url):
        try:
            # Extract the path from URL
            path = urlparse(url).path
            
            # Remove /drug-interactions/ and .html
            path = path.replace('/drug-interactions/', '').replace('.html', '')
            
            # -with- separates two drugs in the URLs
            # Remove that and split to a list
            if '-with-' in path:
                parts = path.split('-with-')
                drug1_part = parts[0]
                drug2_part = parts[1] if len(parts) > 1 else ''
                
                # Removes the numeric ID applied to each
                drug1 = re.sub(r'-\d+(-\d+)*$', '', drug1_part)
                drug2 = re.sub(r'-\d+(-\d+)*$', '', drug2_part)

                # Exception handling for parsing
                return (drug1, drug2)
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
        
        return None

    # Searches the two drugs to find any listed interaction
    # Returns URL if exists, nothing if not
    def check_interaction(self, drug1, drug2):
        # Normalize both drug inputs from user
        drug1_norm = self.normalize_drug_name(drug1)
        drug2_norm = self.normalize_drug_name(drug2)

        # Set a list for the URLs
        matching_urls = []

        # Loop through URL Directory
        for url in self.interactions:
            drugs = self.extract_drugs_from_url(url)
            
            if drugs:
                url_drug1, url_drug2 = drugs
                
                # Reorder drugs then try search again
                if ((drug1_norm == url_drug1 and drug2_norm == url_drug2) or
                    (drug2_norm == url_drug1 and drug1_norm == url_drug2)):
                    matching_urls.append(url)
        
        return matching_urls

    # Searches interactions that do exist from the HTML results
    # From the list, checks if the interactions were found
    def search_drug_interactions(self, drug1, drug2):

        # Series of print statements to check interactions
        print(f"\nSearching for interactions between '{drug1}' and '{drug2}'...")
        print("-" * 70)

        # set interaction to a string
        results = self.check_interaction(drug1, drug2)

        # Confirm results for the user
        if results:
            print(f"\n✓ INTERACTION FOUND: {len(results)} interaction(s) detected!\n")
            # We don't print the list here anymore to keep I/O clean
            return results
        else:
            print(f"\n✗ No interaction found between '{drug1}' and '{drug2}'.")
            print("Note: This doesn't guarantee safety - always consult a healthcare professional.")
            return []

# main() to run the drug interaction checks
def get_drug_interactions(drug1, drug2):

    # List all the XML files to search
    xml_files = [
        "drug-drug-interactions/drug-drug-interactions.xml",
        "drug-drug-interactions/drug-drug-interactions2.xml",
        "drug-drug-interactions/drug-drug-interactions3.xml",
        "drug-drug-interactions/drug-drug-interactions4.xml",
        "drug-drug-interactions/drug-drug-interactions5.xml",
    ]

    results = []

    for xml_file in xml_files:
        # Create parser and check interaction
        parser = DrugInteractionParser(xml_file)
        results = parser.search_drug_interactions(drug1, drug2)

    # Initialize the Output Array with defaults
    # [0] Drug 1, [1] Drug 2, [2] Severity, [3] URL, [4] Description, [5] Extras
    output_array = [drug1, drug2, "N/A", "N/A", "No interaction found", {}]

    if results and len(results) > 0:
        # Use the first URL found
        url = results[0]
        output_array[3] = url

        # Run the Scraper to fill the rest of the array
        scraper = DrugInteractionScraper(url)
        data = scraper.scrape_all()
        
        if data:
            # [0] - Drug 1 (Update with formal name if found)
            output_array[0] = data.get('drug1', drug1)
            
            # [1] - Drug 2 (Update with formal name if found)
            output_array[1] = data.get('drug2', drug2)
            
            # [2] - Severity
            output_array[2] = data.get('severity', "Unknown")
            
            # [4] - Side Effect Description
            # Get the first description or default message
            descs = data.get('description', [])
            output_array[4] = descs[0] if descs else "Description not extracted"
            
            # [5] - Everything else (Professional info, references, etc)
            extras = {}
            if 'professional_info' in data:
                extras['professional_info'] = data['professional_info']
            if 'references' in data:
                extras['references'] = data['references']
            # Include all descriptions if there are multiple
            if descs and len(descs) > 1:
                extras['all_descriptions'] = descs
            
            output_array[5] = extras

    # OUTPUT: Print the single-line formatted string
    print("\n" + "=" * 70)
    print("INTERACTION SUMMARY")
    print("=" * 70)

    # Format: drug1 drug2 \n Applies to: drug1 and drug2 \n description \n URL
    if output_array[2] != "N/A" and output_array[4] != "No interaction found":
        summary = f"{output_array[0]} {output_array[1]}\nApplies to: {output_array[0]} and {output_array[1]}\n{output_array[4]}\n{output_array[3]}"
        print(summary)
    else:
        print(f"No interaction found between {drug1} and {drug2}")

    print("\n" + "=" * 70)
    print("FINAL OUTPUT ARRAY")
    print("=" * 70)
    # [0] Drug 1, [1] Drug 2, [2] Severity, [3] URL, [4] Description, [5] Extras
    print(output_array)

if __name__ == "__main__":
    get_drug_interactions("caffeine", "acetate")
