# Drug-Interaction-GUI

These two both face Drugs.com
InteractionScrapterHTML.py + InteractionParserXML.py

These two programs take and parse the drugs.com drug interaction information, creating a
searchable format for the drugs.com interactions then searching that format as many
times as the user needs.

Setup:
- Python 3.6+
- Internet Connection
- Install pip

Install Libraries from pip, open the Terminal/Command line and input
{ pip install requests beautifulsoup4 }
Ensure you have all three files in the same directory
- drug-interactions.xml
- interactionScraperHTML.py
- InteractionXMLParser.py

How to Use:
The code is currently set to be ran then return the interactions for acebutolol and taurine,
these are manually coded into the main() function of InteractionXMLParser. This was done
for testing purposes as I knew they were valid inputs on the 1st XML file.
Both programs have commented out code that can allow for command line functionality
and inputting drug names, feel free to alter the code or ask me to change it.

Data Structure:
InteractionXMLParser

Variables:
xml_file(string)
- Path to the xml_file
drug1, drug2 (strings)
- The two drugs we are parsing for
self.interactions[] (list)
- All the retrieved interaction URLS from the XML file
results[] (list)
- The matching URL from the XML file

Functions:
__init__(xml_file_path)
- Initializes the xml parsers and calls the parse_xml() function
parse_xml()
- Reads and extracts the URLs from the XML files, stores them to self.interactions
normalize_drug_name(drug_name)
- Makes drug names lowercase and removes spaces
extract_drugs_from_url(url)
- Parses URL for drug names and removes numeric IDs to leave with a string
check_interaction(drug1, drug2)
- Searches for self.interactions for matching drug URLs and returns the matching ones
search_drug_interactions(drug1, drug2)
- Prints the formatted results of the other functions for the drug interactions
InteractionScraperHTML

Variable:
self.url (string)
- URL to scrape
self.html_content (string)
- Raw HTML data
self.soup (BeautifulSoup Obj)
- Parsed HTML Data
self.interaction_data (dictionary)
- All extracted data

Function:
fetch_page() - downloads HTML given to the method
extract_drug_names() - Finds drug names in headers
extract_interaction_severity() - Uses drugs.com 3 danger levels for interaction
extract_interaction_descrition() - Scrapes the paragraph of found by extract_drug_names()
extract_professional_info() - Scrapes info used by medical professionals
extract_references() - Scrapes data references on site
scrape_all() - Runs all commands and saves the data
print_summary() – Prints all the data
save_to_json(outputfile) - Overwrite the output file with the new json file (can be removed)


medlinePlusParsingTool.py

Setup:
- Python 3.6+
- Internet Connection
- Install pip

Install Libraries from pip, open the Terminal/Command line and input
{ pip install requests beautifulsoup4 }

Ensure you have all three files in the same directory
- drug-interactions.xml
- interactionScraperHTML.py
- InteractionXMLParser.py

How to Use:
The code is currently set to accept an input from the user
MedlinePlus was the harder tool to use and parse given its use of group structuring for
sorting which forced us to mimic an input to the website and then pull the HTML request
from that return.

Variables:
First_letter
- Determines the page the URl will come from
index_url
- the html link to the page
drug_name_lower
- A lowercase version of the user input
has_effects
- Boolean checking if the drug has side effects
side_effects_data[]
- Dictionary containing serious, minor, and other side effects
soup
- Beautiful soup object that parses various HTML files
heading()
- Contains each heading used to sort the file
heading_text_lower[]
- Array containing lowercase versions of the headings
category()
- Sorts the severity of side effects
heading_text_lower[]
- Array containing lowercase versions of the headings

Functions:
find_drug_page(string)
- Searches medlinePlus for a drug and returns the title and URL
extracts_side_effects(string)
- Parses a URL for specific keywords to find the side effects of a drug
print_side_effects(drug name, url, side effect data)
- Takes all of the found information then prints it out for the user
save_to_file(drug name, title, url, side effect data)
- Searches for self.interactions for matching drug URLs and returns the matching ones

  


This project includes code and documentation generated with the assistance of ChatGPT (OpenAI), using GPT-5.1 on November 2025.