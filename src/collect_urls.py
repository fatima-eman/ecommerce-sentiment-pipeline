import csv
import re
import time
import random
from playwright.sync_api import sync_playwright

# This script scrapes the top 200 books from Goodreads and saves their titles and URLs to a CSV file.
def scrape_urls():

    # Counter to keep track of how many books have been scraped
    books_scraped_count=0
    # URL of the Goodreads "Best Books Ever" list page to start scraping from
    homepage_url= "https://www.goodreads.com/list/show/1.Best_Books_Ever"

    # Use Playwright to automate the browser and scrape data
    with sync_playwright() as p:
        # Launch the browser in non-headless mode to visually confirm the scraping process
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Navigate to the Goodreads "Best Books Ever" list page
        # Give it 60 seconds to respond, but stop waiting the moment the core HTML document is loaded
        page.goto(homepage_url, wait_until="domcontentloaded", timeout=60000)

        # Open CSV file to save data incrementally
        with open("books_queue.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Book ID", "Book Title", "URL", "Status"])
        
            # Loop through pages and scrape book titles and URLs until we have 200 books
            while books_scraped_count<200:
                print(f"\n--- Scraping Page... Total gathered so far: {books_scraped_count} ---")
                
                # Wait for the book title elements to load on the page
                page.wait_for_selector("a.bookTitle")
                # Get all book title elements on the current page
                book_elements= page.locator("a.bookTitle").all()
                
                # Loop through each book element and extract the title and URL, while keeping track of how many books have been scraped
                for book in book_elements:
                    if books_scraped_count>=200:
                        break
                    try:
                        # Extract the book title and URL, and save them to the CSV file
                        title = book.locator("span[itemprop='name']").inner_text()

                        relative_url= book.get_attribute("href")
                        url= f"https://www.goodreads.com{relative_url}"

                        match = re.search(r"/show/(\d+)", relative_url)
                        book_id = match.group(1) if match else "unknown"

                        print(f"Scraped: [{book_id}] {title}")

                        writer.writerow([book_id, title, url, "Pending"])
                    except Exception as e:
                        print(f"Error occurred while scraping book: {e}")   
                    books_scraped_count+=1
                # Check if we have scraped 200 books, if not, try to navigate to the next page
                if books_scraped_count<200:
                    try:
                        # Target only the link that specifically reads "Next →"
                        next_button = page.get_by_role("link", name="Next →")
                        if next_button.count() == 0:
                            print("No clickable next page element found. Reached final page.")
                            break

                        # Track current URL before clicking to verify page transition
                        current_url = page.url
                        next_button.click()


                        try:
                            page.wait_for_function(f"window.location.href !== '{current_url}'", timeout=10000)
                            time.sleep(random.uniform(1.5, 3.0)) # Polite throttle delay
                        except Exception:
                            print("Timeout waiting for page navigation.")
                            break
                        
                    except Exception as e:
                        print(f"Error occurred while navigating to the next page: {e}")
                        break
                else:
                    print("Reached the target of 200 books. Stopping.")
                    break
        browser.close()

if __name__ == "__main__":
    scrape_urls()
