# 📚 Goodreads E-Commerce Sentiment Pipeline

> An enterprise-grade, asynchronous ELT (Extract, Load, Transform) data pipeline designed to extract, store, and process book reviews from Goodreads at scale. This data is normalized specifically for downstream Natural Language Processing (NLP) and sentiment analysis.

---

## 🏗️ Architecture Overview

This project strictly adheres to the **ELT (Extract, Load, Transform)** data engineering paradigm, ensuring that raw data is captured and preserved with high fidelity before any destructive cleaning occurs.

### 🕸️ Phase 1: Extract
Built with Python's `asyncio` and `playwright.async_api`, the extraction engine reads targets from a master `books_queue.csv` and systematically scrapes reviews.
* **Targeted UI Filters:** Automatically applies strict sorting criteria (Newest, English, This Edition).
* **React-Safe Pagination:** Navigates modern virtualized React lists and bypasses hard-navigation traps by utilizing bounding box pixel checks to execute React-friendly clicks.
* **Dynamic Target Limits:** Extracts up to 1,000 reviews per book. If a book has fewer than 1,000 reviews, the orchestrator safely catches a `TimeoutError` at the end of the pagination list and gracefully completes the extraction.
* **Resilience & Anti-Bot Defenses:** Features randomized human-pacing delays, dynamic ad-sweeping, and an asynchronous background listener to intercept and dismiss sticky sign-up pop-ups without interrupting the main loop.

### 💾 Phase 2: Load
Focuses on strict DOM preservation to maintain data integrity.
* **Native Storage:** Uncleaned HTML structures (including spoiler tags, emojis, and formatting) are mapped to unique User IDs and serialized directly into JSON documents.
* **File Management:** Datasets are saved dynamically to the `data/raw/` directory using an OS-safe filename format: `{safe_book_title}_{book_id}.json`.
* **State Reconciliation (Idempotency):** The orchestrator cross-references existing JSON payloads on the local disk against the master CSV tracker. This allows the pipeline to instantly resume interrupted scrapes, merge partial datasets, and skip fully processed books without duplicating data or throwing file lock errors.

### 🧹 Phase 3: Transform
Parses and normalizes the raw HTML into tabular-ready structures for machine learning.
* **HTML Parsing:** Utilizes `BeautifulSoup` to iterate over raw JSON documents and systematically decompose hidden spoiler (`<details>`) tags so hidden text does not leak into the clean dataset.
* **Data Normalization:** Strips remaining structural HTML tags (like `<br>`) to extract clean plain text. **Native emojis are explicitly preserved**, as they are critical for accurate downstream sentiment scoring.
* **Tabular JSON Output:** Cleaned text is repackaged into normalized JSON arrays and written to the `data/processed/` directory.
* **Queue Synchronization:** Safely updates the master CSV status to `Data_Cleaned` upon successful transformation, utilizing a temporary file swap (`.tmp`) to prevent master file corruption.

---

## 🗂️ Directory Structure

```text
project_root/
├── data/
│   ├── raw/                   # Contains raw, uncleaned JSON extraction files (DOM preserved)
│   └── processed/             # Contains cleaned, normalized JSON arrays ready for NLP
├── src/
│   ├── config.py              # Centralized constants, CSS selectors, and path resolutions
│   ├── collect_urls.py        # Generates the initial books_queue.csv targets
│   ├── extract_reviews.py     # Async Playwright scraper (Phase 1) and raw JSON loader (Phase 2)
│   └── transform_reviews.py   # BeautifulSoup HTML parsing and normalization script (Phase 3)
├── books_queue.csv            # Master job queue (Book ID, Title, URL, Status)
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

---

## 💾 Data Schema Transformation

**Raw Input (`data/raw/`)**  
Preserves the exact DOM structure, mapped by User ID.
```json
{
    "12345678": "<section class=\"ReviewText__content\">The Hunger Games is an amazing book! <br> <b>Highly recommended.</b> 🔥</section>",
    "87654321": "<section class=\"ReviewText__content\">Could not put it down. <details>Spoiler alert hidden here</details></section>"
}
```

**Processed Output (`data/processed/`)**  
Normalized array structure, stripped of HTML/spoilers but preserving sentiment-heavy emojis.
```json
[
    {
        "user_id": "12345678",
        "cleaned_review": "The Hunger Games is an amazing book! Highly recommended. 🔥"
    },
    {
        "user_id": "87654321",
        "cleaned_review": "Could not put it down."
    }
]
```

---

## 🚀 Getting Started

### 1. Prerequisites & Installation
Ensure you have Python 3.10+ installed. Set up your environment and install the required dependencies:

```bash
# Clone the repository
git clone https://github.com/yourusername/ecommerce-sentiment-pipeline.git
cd ecommerce-sentiment-pipeline

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 2. Execution Workflow

**Step 1: Initialize Queue**
Generate the target URLs in your tracking CSV:
```bash
python src/collect_urls.py
```

**Step 2: Extract & Load (Phases 1 & 2)**
Run the asynchronous scraper. The script will automatically audit progress, skip completed targets, and handle partial resumes:
```bash
python src/extract_reviews.py
```

**Step 3: Transform & Clean (Phase 3)**
Run the transformation engine to parse the HTML and output clean JSON arrays:
```bash
python src/transform_reviews.py
```

---

## 🗺️ Roadmap
- [x] **Phase 1: Extract** (Async web scraping, React-safe pagination, anti-bot defenses)
- [x] **Phase 2: Load** (Raw JSON document serialization & idempotency auditing)
- [x] **Phase 3: Transform** (HTML parsing, text normalization, and JSON array formatting)
- [ ] **Phase 4: Sentiment Analysis** (Scoring reviews via NLP models like VADER or Hugging Face Transformers)
- [ ] **Phase 5: Data Serving & Visualization** (Data warehousing and interactive analytical dashboards)