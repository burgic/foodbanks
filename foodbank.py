import requests
from bs4 import BeautifulSoup
import tldextract
import time
import openai
import os
from dotenv import load_dotenv
import json, re
import axios

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = openai.Client(api_key=OPENAI_API_KEY)

# Regex patterns for extracting contact information
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_PATTERN = r'(?:\+44|0)\s*(?:1|2|3|7|8|9)\d{1,4}\s*\d{3,4}\s*\d{3,4}'
POSTCODE_PATTERN = r'\b[A-Z]{1,2}[0-9][A-Z0-9]?\s*[0-9][A-Z]{2}\b'
UK_ADDRESS_PATTERN = r'\b\d+\s+[A-Za-z\s]+(?:Street|Road|Avenue|Lane|Drive|Close|Way|Place|Court|Crescent|Terrace|Grove|Hill|Park|Square|Mews|Gardens?|Walk|Bridge|Quay|Wharf|Yard|Alley|Arcade|Boulevard|Circle|Commons?|Cross|End|Fields?|Gate|Green|Heath|Highway|Island|Junction|Mall|Market|Meadows?|Mount|Parade|Passage|Path|Piazza|Plaza|Promenade|Rise|Row|Rue|Run|Service|Services|Side|Slip|Spur|Strand|Subway|Thicket|Towers?|Track|Trail|Vale|Viaduct|Villas?|Vista|Walk|Wharf|Wood|Wynd)\b'
OPENING_HOURS_PATTERNS = [
    r'(?:Monday|Mon|M)\s*:?\s*(?:(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)|(?:closed|Closed|CLOSED))',
    r'(?:Tuesday|Tue|T)\s*:?\s*(?:(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)|(?:closed|Closed|CLOSED))',
    r'(?:Wednesday|Wed|W)\s*:?\s*(?:(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)|(?:closed|Closed|CLOSED))',
    r'(?:Thursday|Thu|Th)\s*:?\s*(?:(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)|(?:closed|Closed|CLOSED))',
    r'(?:Friday|Fri|F)\s*:?\s*(?:(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)|(?:closed|Closed|CLOSED))',
    r'(?:Saturday|Sat|Sa)\s*:?\s*(?:(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)|(?:closed|Closed|CLOSED))',
    r'(?:Sunday|Sun|Su)\s*:?\s*(?:(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)|(?:closed|Closed|CLOSED))'
]

SEARCH_LOCATIONS = [
    "Manchester UK", 
    #"Birmingham UK",
    #"Leeds UK",
    #"Liverpool UK",
    #"Sheffield UK",
    #"Bradford UK",
    #"Edinburgh UK",
    #"Glasgow UK",
    #"Cardiff UK",
    # "Bristol UK"
]
SEARCH_TERMS = [
    #"food bank",
    "foodbank",
    #"food pantry",
    #"community pantry"
]



def google_search(query, page=1):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    data = {"q": query, "page": page}
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json().get("organic", [])

def extract_main_content(url):
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        main = soup.find('main')
        text = main.get_text(separator=" ", strip=True) if main else soup.get_text(" ", strip=True)
        return text[:9000]  # Truncate to stay under token limits for GPT-4.1-mini
    except Exception as e:
        return f"Error fetching page: {e}"
    
def extract_contact_info(text):
    """
    Extract contact information from text using regex patterns
    """
    info = {}
    
    # Extract email addresses
    emails = re.findall(EMAIL_PATTERN, text)
    if emails:
        info["Email"] = emails[0]  # Take the first email found
    
    # Extract phone numbers
    phones = re.findall(PHONE_PATTERN, text)
    if phones:
        info["Phone"] = phones[0]  # Take the first phone number found
    
    # Extract postcodes
    postcodes = re.findall(POSTCODE_PATTERN, text)
    if postcodes:
        info["Postcode"] = postcodes[0]  # Take the first postcode found
    
    # Extract UK addresses
    addresses = re.findall(UK_ADDRESS_PATTERN, text)
    if addresses:
        info["Address"] = addresses[0]  # Take the first address found
    
    # Extract opening hours
    opening_hours = []
    for pattern in OPENING_HOURS_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if match:  # If there's a time match (not empty)
                opening_hours.append(match)
    
    if opening_hours:
        info["Opening Hours"] = ", ".join(opening_hours)
    
    return info

def safe_json_extract(text):
    try:
        match = re.search(r"\{[\s\S]+?\}", text)
        if match:
            try:
                parsed = json.loads(match.group(0))
                # Handle cases where Opening Hours is an object instead of string
                if "Opening Hours" in parsed and isinstance(parsed["Opening Hours"], dict):
                    # Convert object to string representation
                    hours_obj = parsed["Opening Hours"]
                    hours_str = ", ".join([f"{day}: {time}" for day, time in hours_obj.items() if time])
                    parsed["Opening Hours"] = hours_str
                return parsed
            except Exception as e:
                return {"error": f"JSON decode failed: {e}", "raw": match.group(0)}
        return {"error": "No JSON found", "raw": text}
    except Exception as e:
        return {"error": str(e), "raw": text}

def classify_page(text):
    """
    Uses GPT to classify whether the page is a single foodbank, a directory, or other.
    """
    prompt = (
        "You are a helpful, very diligent research assistant that classifies webpages as 'single' (about a specific food bank or pantry), 'directory' (a list, directory, guide, review site, or ranking of multiple food banks), or 'other' (not related to food banks).\n\n"
        "Classify this webpage content as:\n"
        "- 'single': about a specific food bank or pantry (even if it's a social media page, listing, or get-help page)\n"
        "- 'directory': a list, directory, guide, review site, or ranking of multiple food banks (even if it's just a few)\n"
        "- 'other': not related to food banks\n\n"
        "Be VERY generous with 'directory' classification:\n"
        "- If it mentions multiple food banks, classify as directory\n"
        "- If it's a review site (like Yelp), classify as directory\n"
        "- If it's a ranking or 'best of' list, classify as directory\n"
        "- If it lists services or resources, classify as directory\n"
        "- If it's a guide or resource page, classify as directory\n"
        "- If the title mentions 'food banks' (plural), likely directory\n\n"
        "Be generous with 'single' classification - if it mentions a food bank name, service, or has 'get-help' in URL, classify as single.\n"
        "Pages with 'get-help', 'find-a-foodbank', or specific food bank names should be 'single'.\n"
        "Only return: single, directory, or other\n\n"
        f"CONTENT:\n{text[:3000]}"
    )
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=10
    )
    result = response.choices[0].message.content.strip().lower()
    if result in {"single", "directory", "other"}:
        return result
    return "other"

def extract_foodbank_links_from_directory(html_content, base_url):
    """
    Extract food bank links from directory pages using multiple methods
    """
    soup = BeautifulSoup(html_content, "html.parser")
    links = []
    
    # Method 1: Direct HTML link extraction with broader terms
    for a in soup.find_all("a", href=True):
        href = a['href']
        text = a.get_text(strip=True).lower()
        
        # Check if link text or href contains food bank related terms
        foodbank_terms = [
            'foodbank', 'food bank', 'pantry', 'food pantry', 'food-bank',
            'foodbank.org', 'foodbank.org.uk', 'trussell', 'turn2us',
            'charity', 'community', 'support', 'help', 'assistance',
            'manchester', 'central', 'south', 'north', 'east', 'west'
        ]
        if any(term in href.lower() or term in text for term in foodbank_terms):
            full_url = href if href.startswith('http') else base_url.rstrip('/') + '/' + href.lstrip('/')
            links.append(full_url)
    
    # Method 2: Look for links in lists, tables, or structured content
    for element in soup.find_all(['li', 'td', 'div', 'p'], class_=lambda x: x and any(term in x.lower() for term in ['food', 'bank', 'pantry', 'charity', 'support', 'help'])):
        for a in element.find_all("a", href=True):
            href = a['href']
            full_url = href if href.startswith('http') else base_url.rstrip('/') + '/' + href.lstrip('/')
            links.append(full_url)
    
    # Method 3: Extract all links and filter by domain patterns
    if not links:
        for a in soup.find_all("a", href=True):
            href = a['href']
            if href.startswith('http'):
                # Look for food bank related domains
                if any(domain in href.lower() for domain in [
                    'foodbank.org.uk', 'foodbank.org', 'trusselltrust.org',
                    'turn2us.org.uk', 'charitycommission.gov.uk',
                    'manchester', 'central', 'south', 'north'
                ]):
                    links.append(href)
    
    # Method 4: If still no links, try to extract from text using GPT
    if not links:
        try:
            prompt = (
                "Extract food bank website URLs from this directory page text. "
                "Look for any mentions of food banks, pantries, charities, or food assistance services. "
                "Also look for organization names that might be food banks. "
                "Return ONLY a JSON array of URLs, nothing else. If no URLs found, return [].\n\n"
                f"TEXT:\n{html_content[:4000]}"
            )
            response = client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=400
            )
            content = response.choices[0].message.content
            # Try to extract URLs from GPT response
            url_matches = re.findall(r'https?://[^\s"\']+', content)
            links.extend(url_matches)
        except Exception as e:
            print(f" GPT link extraction failed: {e}")
    
    
    # Method 5: Extract organization names and try to find their websites
    if not links:
        try:
            prompt = (
                "Extract food bank organization names from this text. "
                "Look for any food banks, pantries, or food assistance organizations mentioned. "
                "Return ONLY a JSON array of organization names, nothing else.\n\n"
                f"TEXT:\n{html_content[:3000]}"
            )
            response = client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=300
            )
            content = response.choices[0].message.content
            # Try to extract organization names and construct potential URLs
            org_matches = re.findall(r'"([^"]+)"', content)
            for org in org_matches:
                if any(term in org.lower() for term in ['food', 'bank', 'pantry', 'charity']):
                    # Try common URL patterns
                    potential_urls = [
                        f"https://{org.lower().replace(' ', '').replace('&', 'and')}.org.uk",
                        f"https://{org.lower().replace(' ', '-').replace('&', 'and')}.org.uk",
                        f"https://www.{org.lower().replace(' ', '').replace('&', 'and')}.org.uk"
                    ]
                    links.extend(potential_urls)
        except Exception as e:
            print(f" Organization name extraction failed: {e}")
    
    # Remove duplicates and filter
    unique_links = list(set(links))
    filtered_links = []
    for link in unique_links:
        # Be more lenient with filtering
        if any(term in link.lower() for term in ['foodbank', 'food-bank', 'pantry', 'food', 'charity', 'org', 'uk', 'manchester']):
            filtered_links.append(link)
    
    return filtered_links


def gpt_parse_foodbank(text):
    try:
        prompt = (
            "You are a helpful, very diligent research assistant that extracts structured data about a UK food bank from the provided website text. "
            "Extract structured data about a UK food bank from the provided website text. "
            "Return ONLY a single JSON object with the following fields: "
            "Name, Address, Postcode, Phone, Email, Opening Hours, Website, Any special requirements. "
            "If any information is missing, use null. Do NOT include explanations, comments, or any extra text. "
            "Only return valid JSON and nothing else.\n\n"
            f"{text[:6000]}"
        )
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=600
        )
        content = response.choices[0].message.content
        gpt_result = safe_json_extract(content)
        
        # If GPT parsing failed or returned incomplete data, try regex extraction
        if "error" in gpt_result or gpt_result.get("Name") is None:
            print("  GPT parsing failed or incomplete, trying regex extraction...")
            regex_info = extract_contact_info(text)
            
            # Merge regex results with GPT results
            if "error" not in gpt_result:
                # Merge regex findings into GPT result
                for key, value in regex_info.items():
                    if gpt_result.get(key) is None and value:
                        gpt_result[key] = value
                        print(f"    Found {key}: {value}")
            else:
                # Use regex results as fallback
                gpt_result = regex_info
                print(f"    Using regex extraction as fallback")
        
        return gpt_result
    except Exception as e:
        # If GPT completely fails, try regex extraction
        print(f"  GPT parsing failed: {e}, trying regex extraction...")
        return extract_contact_info(text)
    
def domain_from_url(url):
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"

results = []

for location in SEARCH_LOCATIONS:
    for term in SEARCH_TERMS:
        # Try different search strategies for each term
        search_queries = [
            f"{term} {location} -Trussell",
            # f"{term} {location}",
            # f"{term} near {location}",
            # f"community {term} {location}"
        ]
        
        all_search_results = []
        
        for query in search_queries:
            print(f"Searching: {query}")
            
            # Get results from multiple pages
            for page in range(1, 4):  # Try pages 1, 2, 3
                try:
                    page_results = google_search(query, page=page)
                    all_search_results.extend(page_results)
                    print(f" Page {page}: {len(page_results)} results")
                    if len(page_results) == 0:
                        break  # No more results
                except Exception as e:
                    print(f" Error on page {page}: {e}")
                    break
        
        print(f" Total: {len(all_search_results)} search results")
        for res in all_search_results[:30]:  # Process up to 30 results
            url = res.get("link")
            name = res.get("title")
            domain = domain_from_url(url)
            print(f" Scraping {url} ({name})")
            main_text = extract_main_content(url)
            if main_text.startswith("Error"):
                structured = {"error": main_text}
            else:
                # Check URL for obvious directory indicators
                url_lower = url.lower()
                if any(term in url_lower for term in ['yelp', 'search', 'list', 'directory', 'find', 'best', 'top', 'review']):
                    classification = "directory"
                    print(f"  Classified as: directory (URL indicator)")
                else:
                    classification = classify_page(main_text)
                    print(f"  Classified as: {classification}")
                
                if classification == "directory":
                    # Extract individual links and process them
                    print(f" Directory page: extracting links from {url}")
                    # Get the HTML content for better link extraction
                    try:
                        resp = requests.get(url, timeout=10)
                        html_content = resp.text
                    except Exception as e:
                        html_content = main_text
                    
                    foodbank_links = extract_foodbank_links_from_directory(html_content, url)
                    print(f"  Found {len(foodbank_links)} food bank links")
                    
                    for fb_url in foodbank_links[:5]:  # Limit to 5 to avoid too many requests
                        print(f"    Processing: {fb_url}")
                        fb_main_text = extract_main_content(fb_url)
                        if fb_main_text and not fb_main_text.startswith("Error"):
                            fb_structured = gpt_parse_foodbank(fb_main_text)
                            # Save as another record
                            results.append({
                                "name": fb_url,
                                "url": fb_url,
                                "domain": domain_from_url(fb_url),
                                "location": location,
                                "structured": fb_structured,
                            })
                        time.sleep(1)  # Be nice to individual food bank sites
                    
                    structured = {"error": f"Directory page processed, extracted {len(foodbank_links)} links"}
                elif classification != "single":
                    structured = {"error": f"Skipped page classified as '{classification}'"}
                else:
                    structured = gpt_parse_foodbank(main_text)
            record = {
                "name": name,
                "url": url,
                "domain": domain,
                "location": location,
                "structured": structured,
            }
            results.append(record)
            time.sleep(2)  # Be nice!

# Deduplicate: By (Address if found) else by domain
unique = {}
for r in results:
    addr = None
    try:
        addr = (r["structured"].get("Address") or "").strip().lower()
    except:
        pass
    key = addr if addr else r["domain"]
    if key and key not in unique:
        unique[key] = r

foodbanks = list(unique.values())

for fb in foodbanks:
    print(json.dumps(fb, indent=2, ensure_ascii=False))
