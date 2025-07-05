# foodbanks

# UK Foodbank Data Crawler

**Find, extract, and structure data about foodbanks across the UK — including non-Trussell Trust sites — using Google Search (Serper API), web scraping, and OpenAI for intelligent parsing.**

---

## Features

- Searches for foodbanks using multiple query types and paginated Google Search via [Serper API](https://serper.dev/)
- Scrapes data from individual foodbank websites and aggregator/directory pages
- Extracts structured info (name, address, phone, opening hours, requirements, etc.) from HTML or raw text using OpenAI GPT models
- Filters out directories/irrelevant pages automatically
- Deduplicates results and outputs as JSON
- Easily extensible for more search terms, locations, or output formats

---

## Requirements

- Node.js (for search scripts)
- Python 3 (for scraping & OpenAI parsing)
- [Serper API key](https://serper.dev/)
- [OpenAI API key](https://platform.openai.com/)
- Python libraries: `requests`, `beautifulsoup4`, `tldextract`, `openai`
- Node.js libraries: `axios`

---

## Usage

### 1. **Set Up Environment**

Clone the repo and install dependencies:

```bash
git clone https://github.com/yourusername/your-repo.git
cd your-repo

# For Python
pip install -r requirements.txt

# For Node.js
npm install
