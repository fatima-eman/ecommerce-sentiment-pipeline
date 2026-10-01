import csv
import json
import re
import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError
# Import cleanly isolated configuration module from your project path
from config import PipelineConfig
def get_json_filepath(book_id: str, book_title: str, config: PipelineConfig) -> Path:
    """Consistently generates the safe file path for a book's JSON file."""
    # Sanitize the book title to prevent OS file path errors
    safe_title = re.sub(r'[\\/*?:"<>|]', "", book_title).strip()
    safe_title = safe_title.replace(" ", "_")
    
    filename = f"{safe_title}_{book_id}.json"
    return config.RAW_DATA_DIR / filename

# =====================================================================
# 1. JOB QUEUE CONTROLLER (State Reconciliation)
# =====================================================================
def audit_and_get_pending_books(queue_file: Path, config: PipelineConfig) -> list:
    """
    Reads the tracking queue and cross-references it with local JSON files.
    If a JSON document contains >= TARGET_REVIEWS_PER_BOOK, updates the CSV status.
    Returns only the books that genuinely need scraping.
    """
    pending_books = []
    updated_rows = []
    
    if not queue_file.exists():
        print(f"❌ [Queue Error] File not found at: {queue_file}. Run Phase 1 first!")
        return pending_books

    print("🔄 [State Management] Auditing queue against local disk storage...")
    
    with open(queue_file, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        
        for row in reader:
            status = row.get("Status", "").strip().lower()
            book_id = row.get("Book ID", "").strip()
            book_title = row.get("Book Title", "").strip()
            
            # Only audit books currently marked as pending
            if status == "pending":
                file_path = get_json_filepath(book_id, book_title, config)
                
                if file_path.exists():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            existing_reviews = json.load(f)
                            
                        # Check if the book has met the extraction criteria
                        if len(existing_reviews) >= config.TARGET_REVIEWS_PER_BOOK:
                            print(f"✅ [Audit] '{book_title}' is fully scraped. Updating CSV to 'Raw_Extracted'.")
                            row["Status"] = "Raw_Extracted"
                        else:
                            # Partially scraped books remain pending
                            pending_books.append(row)
                    except json.JSONDecodeError:
                        print(f"⚠️ [Audit Warning] Corrupted JSON found for '{book_title}'. Remaining Pending.")
                        pending_books.append(row)
                else:
                    # No file exists yet
                    pending_books.append(row)
            
            updated_rows.append(row)
            
    # Safely overwrite the original CSV with the updated statuses
    temp_file = queue_file.with_suffix('.tmp')
    with open(temp_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
        
    temp_file.replace(queue_file)
    
    print(f"📊 [Queue Status] Audit complete. Found {len(pending_books)} books requiring extraction.")
    return pending_books

def update_book_status_live(queue_file: Path, target_book_id: str, new_status: str):
    """Updates a single book's status in the CSV immediately after a successful load phase."""
    updated_rows = []
    fieldnames = []
    
    with open(queue_file, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("Book ID", "").strip() == target_book_id:
                row["Status"] = new_status
            updated_rows.append(row)
            
    temp_file = queue_file.with_suffix('.tmp')
    with open(temp_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    temp_file.replace(queue_file)

# =====================================================================
# 2 LOAD LAYER (ELT: Saving Raw Data to Target Destination)
# =====================================================================
def load_raw_reviews_to_json(book_id: str, book_title: str, reviews_data: dict, config: PipelineConfig) -> bool:
    """
    Serializes the raw extracted dictionary into a JSON document.
    File naming convention: {book_title}_{book_ID}.json
    """
    print(f"💾 [Load Phase] Preparing to write raw dataset to storage...")
    
    if not reviews_data:
        print("⚠️ [Load Phase] No data provided. Skipping file creation.")
        return False

    # Sanitize the book title to prevent OS file path errors (removes \ / : * ? " < > |)
    safe_title = re.sub(r'[\\/*?:"<>|]', "", book_title).strip()
    # Replace spaces with underscores for cleaner filenames (optional but recommended)
    safe_title = safe_title.replace(" ", "_")
    
    filename = f"{safe_title}_{book_id}.json"
    
    # Ensure the target directory (data/raw/) exists before trying to write
    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    file_path = config.RAW_DATA_DIR / filename
    
    try:
        # Write to JSON with UTF-8 to preserve emojis, special characters, and raw HTML formatting
        with open(file_path, mode="w", encoding="utf-8") as json_file:
            json.dump(reviews_data, json_file, ensure_ascii=False, indent=4)
            
        print(f"✅ [Load Phase] Successfully stored {len(reviews_data)} reviews at: {file_path}")
        return True
    except Exception as e:
        print(f"❌ [Load Phase Error] Failed to write JSON document to disk: {str(e)}")
        return False

# =====================================================================
# 3. EXTRACTION LAYER (Separation of Concerns: Web Interactions Only)
# =====================================================================
class GoodreadsScraper:
    """Encapsulates the automated browser instance, defensive interceptors,

    and atomic page navigation actions.
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.browser = None
        self.context = None
        self.page = None
    
    # --- New Method: Initialization with Immediate Defense Arming ---
    # =================================================================
    async def initialize_pipeline(self, playwright_instance) -> None:
        # Launches the sandboxed browser environment and configures human traits.
        print("🌐 Launching automated browser instance...")
        
        # Headless=False allows you to visually audit  defenses during runtime
        self.browser = await playwright_instance.chromium.launch(headless=False)
        
        # Inject standard human fingerprint (User Agent) to clear low-level firewalls
        self.context = await self.browser.new_context(
            user_agent=self.config.USER_AGENT
        )
        self.page = await self.context.new_page()
        
        # IMMEDIATELY arm the pop-up defense system right after launching the page
        await self._register_popup_defense()

    # --- New Method: Proactive Pop-up Interception System ---
    async def _register_popup_defense(self) -> None:
        """Registers a low-level asynchronous listener in Playwright's engine.

        Fires automatically whenever the sign-up modal blocks the screen.
        """
        popup_locator = self.page.locator(self.config.POPUP_CLOSE_SELECTOR)
        
        # Define the asynchronous callback function that will execute when the pop-up is detected
        async def dismiss_popup(blocking_element):
            print("\n🛡️  [Pop-up Interceptor] Goodreads registration window detected! Intercepting...")
            try:
                # Atomically click the exit button to clear the UI thread
                await blocking_element.click()
                print("✅ [Pop-up Interceptor] Modal successfully closed. Resuming execution loop.")
                # Give the UI thread a brief moment to settle structural animations
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"⚠️  [Pop-up Interceptor] Interception attempt timed out or failed: {e}")

        # Bind the observer pattern: whenever popup_locator appears, execute dismiss_popup
        await self.page.add_locator_handler(popup_locator, dismiss_popup)
        print("🛡️  [System Status] Continuous background pop-up interceptor successfully armed.")

    # --- New Method: Dual-Layered Navigation with Human Mimicking ---
    async def navigate_to_book(self, book_url: str) -> bool:
        """Executes a dual-layered, fault-tolerant navigation to the book landing page.

        Applies human-like pacing parameters upon arrival.
        """
        print(f"\n🚀 Initiating connection to: {book_url}")
        
        try:
            # Layer 1: Core Navigation via structural DOM presence
            await self.page.goto(
                book_url, 
                wait_until="domcontentloaded", 
                timeout=self.config.PRIMARY_TIMEOUT_MS
            )
            print("📶 [Network Status] Primary connection established. DOM structural layout ready.")
            
        except TimeoutError:
            # Layer 2: Network Latency Fallback Exception Handling
            print("🚨 [Network Latency Alert] Primary timeout exceeded. Deploying backup extension...")
            try:
                await self.page.goto(
                    book_url, 
                    wait_until="domcontentloaded", 
                    timeout=self.config.FALLBACK_TIMEOUT_MS
                )
                print("📶 [Network Status] Backup connection established successfully.")
            except TimeoutError:
                print("❌ [Fatal Network Error] Host completely unreachable within timeline. Skipping target.")
                return False

        # --- Human Mimicking Component ---
        # Fixed delays trigger bot profiles. Float ranges simulate random cognitive delays.
        human_pacing_delay = random.uniform(2.5, 4.5)
        print(f"⏳ [Human Mimicking] Pausing for {human_pacing_delay:.2f} seconds to simulate real reading pace...")
        await asyncio.sleep(human_pacing_delay)
        
        return True

    # --- New Method: Resource Management Layer ---
    async def close_pipeline(self) -> None:
        """Safely deallocates browser memory buffers and stops all threads."""
        if self.browser:
            print("\n🛑 Shutting down browser resources and safely closing down connection channels.")
            await self.browser.close()
    
    # --- New Method: Filter Interaction Layer ---
    async def trigger_filter_popup(self) -> bool:
        """Locates and clicks the primary review filters control button 
        to expose the filter configurations menu.
        """
        print("🔍 [Interaction] Locating the review filter controls...")
        try:
            # Create locator for the button and filter context using the config blueprint
            filter_btn = self.page.locator(self.config.FILTER_BUTTON_SELECTOR)
            
            # Wait until the element is attached to the layout and ready to receive pointer events
            await filter_btn.wait_for(state="visible", timeout=15000)
            
            # Additional assertion: Ensure it contains the expected text label before execution
            button_text = await filter_btn.inner_text()
            if "Filters" in button_text:
                print(f"🎯 [Interaction] Verified button label: '{button_text.strip()}'. Clicking filter trigger...")
                await filter_btn.click()
                
                # Add a brief, natural delay for the DOM to process the click event and paint the popup
                await asyncio.sleep(random.uniform(1.5, 2.5))
                return True
            else:
                print(f"⚠️ [Interaction Warning] Selector found, but unexpected text context: '{button_text}'")
                return False
                
        except TimeoutError:
            print("❌ [Interaction Error] The Filter button could not be resolved or was hidden within timeout limits.")
            return False
        except Exception as e:
            print(f"❌ [Interaction Error] Failed to interact with filter section: {str(e)}")
            return False
        
    # --- New Method: Filter Configuration Matrix ---
    # =================================================================
    async def apply_review_filters(self, page)-> bool:
        """
        Interacts with the open filters overlay menu to configure:
        Sort order -> Newest, Edition -> This Edition, Language -> English.
        """
        print("[Filters Engine] Processing options configuration matrix...")
        
        try:
        
            # 1. Wait explicitly for the modal container overlay to render completely in view
            # Use the locator API for lazy evaluation and compound checks
            modal_locator = page.locator(self.config.FILTERS_MODAL_SELECTOR)
            await modal_locator.wait_for(state="visible", timeout=30000)
            # 2. Select the 'Newest' Sort Order Option
            # We try to click the exact radio node, fallback on text matching if overlaid by UI layout decorators
            try:
                await page.click(self.config.RADIO_NEWEST_SELECTOR, timeout=20000)
            except TimeoutError:
                await page.click("text=Newest first")
            print("[Filters Engine] Sort Order updated to 'Newest'.")
            await asyncio.sleep(random.uniform(0.3, 0.7)) # Human-like toggle pause
            
            # 3. Select the 'Reviews of this edition' Option
            try:
                await page.click(self.config.RADIO_THIS_EDITION_SELECTOR, timeout=20000)
            except TimeoutError:
                await page.click("text=Reviews of this edition") # Alternate text label match
            print("[Filters Engine] Context constrained to current text edition.")
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
            # 4. Select the 'English' Language Option
            try:
                await page.click(self.config.RADIO_ENGLISH_SELECTOR, timeout=20000)
            except TimeoutError:
                await page.click("text=English")
            print("[Filters Engine] Language filter locked to English strings.")
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # 5. Execute Action Submit & Handle Network Re-evaluations
            print("[Filters Engine] Enforcing programmatic internal scroll to uncover action footer...")
            await modal_locator.evaluate("el => el.scrollTo(0, el.scrollHeight)")
        
            # Give the UI layout state machine a brief humanized heartbeat to redraw elements
            await asyncio.sleep(random.uniform(0.6, 1.2))
            
            # 3. Target the Action Apply Button with a resilient fallback mechanism
            # If your strict selector string fails, we use a role fallback strategy to guarantee matching
            apply_button = page.locator(self.config.APPLY_FILTERS_BUTTON_SELECTOR).or_(
                page.get_by_role("button", name="Apply")
            ).or_(
                page.locator("div.overlay__actions button")
            )
            
            print("[Filters Engine] Ready to commit settings. Dispatching apply event...")
            await apply_button.wait_for(state="visible", timeout=15000)
            await apply_button.click(force=True)
                
            print("[Filters Engine] Filters applied successfully! Layout sequence updated.")
            # FIX: Instead of checking page navigation, ensure the modal dismisses itself successfully
            try:
                await modal_locator.wait_for(state="hidden", timeout=10000)
                print("[Filters Engine] Filters modal closed. Layout sequence updated.")
            except TimeoutError:
                print("[Filters Engine] Warning: Modal did not transition to hidden state, proceeding anyway.")
            
            # Baseline pacing delay to allow AJAX elements to cleanly fetch and redraw new review items
            await asyncio.sleep(random.uniform(1.5, 3.0))
            return True
        except Exception as e:
            print(f"❌ [Filters Engine Error] Critical failure during configuration phase: {str(e)}")
            raise e



    # =================================================================
    #Reviews Scpraper Methods
    # =================================================================
   
    # --- New Method: Single-Page Raw Extraction (Step 1) ---
    # =================================================================
    async def extract_reviews_on_current_page(self) -> dict:
        """
        Extracts raw review elements from the current page layout.
        Returns a dictionary mapping User IDs to their raw review HTML.
        """
        page_reviews = {}
        print("🔍 [Extraction] Scanning current layout for review blocks...")
        
        try:
            # Wait for review cards to attach to the DOM
            await self.page.wait_for_selector(self.config.REVIEW_CARD_SELECTOR, timeout=10000)
            
            # Locate all review cards currently rendered on screen
            review_cards = await self.page.locator(self.config.REVIEW_CARD_SELECTOR).all()
            
            for card in review_cards:
                try:
                    # 1. Extract User ID
                    user_link_element = card.locator(self.config.REVIEWER_LINK_SELECTOR).first
                    user_href = await user_link_element.get_attribute("href")
                    
                    # Expected format: "/user/show/12345678-username" -> Extract just the digits
                    import re
                    user_id_match = re.search(r"/show/(\d+)", str(user_href))
                    user_id = user_id_match.group(1) if user_id_match else f"unknown_{random.randint(1000,9999)}"
                    
                    # 2. Extract Raw Review HTML (Strict ELT: No text cleaning here)
                    review_text_element = card.locator(self.config.REVIEW_TEXT_SELECTOR).first
                    raw_review_content = await review_text_element.inner_html()
                    
                    # Map the user ID to their raw review block
                    page_reviews[user_id] = raw_review_content.strip()
                    
                except Exception as e:
                    # Skip corrupted cards gracefully without breaking the loop
                    continue
                    
            print(f"📄 [Extraction] Successfully pulled {len(page_reviews)} reviews from current layout.")
            return page_reviews
            
        except TimeoutError:
            print("⚠️ [Extraction Warning] No review cards found within timeout. Page layout might be empty.")
            return {}

    # =================================================================
    # --- Updated Method: Pagination Engine (Dynamic Exhaustion Fix) ---
    # =================================================================
    async def extract_all_reviews(self, existing_reviews: dict = None) -> tuple[dict, bool]:
        """
        Handles the pagination loop, aggregating reviews until TARGET_REVIEWS_PER_BOOK
        is reached or the pagination button is exhausted.
        Returns: (reviews_dictionary, is_fully_scraped_boolean)
        """
        all_reviews = existing_reviews.copy() if existing_reviews else {}
        is_complete = False
        
        while len(all_reviews) < self.config.TARGET_REVIEWS_PER_BOOK:
            print(f"🔄 [Pagination] Progress: {len(all_reviews)} / {self.config.TARGET_REVIEWS_PER_BOOK} reviews gathered.")
            
            # 1. Extract the current state of the DOM
            current_batch = await self.extract_reviews_on_current_page()
            
            initial_count = len(all_reviews)
            all_reviews.update(current_batch)
            new_count = len(all_reviews)
            
            # Exit condition 1: Reached target
            if len(all_reviews) >= self.config.TARGET_REVIEWS_PER_BOOK:
                print("🎯 [Pagination] Target review limit reached!")
                is_complete = True
                break
                
            # Exit condition 2: No new reviews found in DOM after a successful click cycle
            if new_count == initial_count and initial_count > 0:
                print("⚠️ [Pagination] No new unique reviews detected. Assuming end of available data.")
                is_complete = True
                break
                
            print("📜 [Pagination] Scrolling to bottom of the page...")
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2.0)
            
            popup_close_btn = self.page.locator(self.config.POPUP_CLOSE_SELECTOR).first
            if await popup_close_btn.is_visible():
                await popup_close_btn.click(force=True)
                await asyncio.sleep(1.0)
                
            # 3. Locate and click the correct pagination button
            try:
                robust_selector = (
                    "a[aria-label='Tap to show more reviews and ratings'], "
                    "button:has(span[data-testid='loadMore'])"
                )
                
                await self.page.wait_for_selector(robust_selector, state="visible", timeout=10000)
                next_button = self.page.locator(robust_selector).last
                
                await next_button.scroll_into_view_if_needed()
                await asyncio.sleep(1.0)
                
                print("🖱️ [Pagination] Button detected in DOM. Clicking...")
                await next_button.click()
                
                print("⏳ [Pagination] Waiting for network to fetch and append new reviews...")
                await asyncio.sleep(random.uniform(3.0, 5.0))
                
                if await popup_close_btn.is_visible():
                    print("🛡️ [Pagination Defense] Post-click popup detected! Manually dismissing...")
                    await popup_close_btn.click(force=True)
                    await asyncio.sleep(1.0)
                    
            except TimeoutError:
                # When the button vanishes, the book's total review list is exhausted
                print("🛑 [Pagination] 'Show more' button could not be found. Reached final page.")
                is_complete = True
                break
            except Exception as e:
                print(f"❌ [Pagination Error] Unexpected error during pagination: {e}")
                is_complete = False  # Mark incomplete so idempotency re-tries it later
                break
                
        # Safety fallback check
        if len(all_reviews) >= self.config.TARGET_REVIEWS_PER_BOOK:
            is_complete = True
            
        final_dataset = dict(list(all_reviews.items())[:self.config.TARGET_REVIEWS_PER_BOOK])
        print(f"✅ [Pagination Complete] Successfully compiled {len(final_dataset)} raw reviews.")
        
        return final_dataset, is_complete
    
# =====================================================================
# 4. COORDINATION & ORCHESTRATION LAYER (The Conductor Loop)
# =====================================================================
async def main():
    # Instantiate immutable configuration settings
    config = PipelineConfig()
    
    print("📋 Initializing Job Queue Verification...")
    queue = audit_and_get_pending_books(config.QUEUE_CSV_PATH, config)
    print(f"📊 Tracking Dataset Results: Detected {len(queue)} books waiting in 'Pending' state.")
    
    if not queue:
        print("⚠️  No pending operations inside queue. Pipeline execution aborted.")
        return
        
    # Extract based on config constraints (e.g., up to 3 books for testing)
    test_batch = queue[:config.MAX_BOOKS_TO_PROCESS]
    print(f"🚀 [Pipeline Batch] Extracted up to {len(test_batch)} books for interactive testing cycle.")
    
    # Initialize Context-Managed Async Playwright Engine
    async with async_playwright() as p:
        scraper = GoodreadsScraper(config)
        await scraper.initialize_pipeline(p)
        
        try:
            for index, book in enumerate(test_batch, start=1):
                book_title = book.get("Book Title", "").strip() or f"Book Reference #{index}"
                book_url = book.get("URL", "").strip()
                book_id = book.get("Book ID", "").strip()

                print(f"\n📖 [Processing {index}/{len(test_batch)}]: '{book_title}'")
                print(f"🔗 URL: {book_url}")
                
                # Test navigation runtime, error handlings, and interceptor status
                navigation_success = await scraper.navigate_to_book(book_url)
                
                if navigation_success:
                    # Apply an immediate localized human simulation pacing delay upon successful load
                    human_delay = random.uniform(2.5, 4.5)
                    print(f"⏳ [Defense] Applying behavioral delay of {human_delay:.2f}s...")
                    await asyncio.sleep(human_delay)
                    
                    # NEW LAYER INTEGRATION: Trigger the filter pop-up panel context
                    filter_success = await scraper.trigger_filter_popup()
                    
                    if filter_success:
                        print(f"✅ [Milestone] Filter menu opened successfully for book: '{book_title}'")
                        # NEW LAYER INTEGRATION: Execute choices matrix (Sort order, Edition, Language)
                        filters_applied=await scraper.apply_review_filters(scraper.page)
                        if filters_applied:
                            print(f"✅ [Milestone] Filters applied successfully for book: '{book_title}'")

                            # --- ELT PHASE: EXTRACT ---
                            print(f"⚙️ [Pipeline] Initiating raw data extraction phase...")
                            
                            # Unpack the new boolean flag returned by the extractor
                            raw_reviews_data, is_complete = await scraper.extract_all_reviews()
                            
                            # --- ELT PHASE: LOAD ---
                            if raw_reviews_data:
                                success = load_raw_reviews_to_json(book_id, book_title, raw_reviews_data, config)
                                
                                # If the data saved cleanly AND the scraper confirmed the list is exhausted/hit target
                                if success and is_complete:
                                    print(f"✅ [Status Update] Marking '{book_title}' as 'Raw_Extracted' in CSV.")
                                    update_book_status_live(config.QUEUE_CSV_PATH, book_id, "Raw_Extracted")
                            else:
                                print(f"⚠️ [Pipeline] No reviews extracted for '{book_title}'. Skipping load phase.")

                        else: 
                            print(f"❌ [Milestone Failed] Filter configuration failed for book: '{book_title}'")
                    else:
                        print(f"❌ [Milestone Failed] Could not trigger filter menu for book: '{book_title}'")

                else:
                    print(f"❌ Navigation Failed! Skipping execution loops for this target record.")
                
                # Apply a cooldown delay between distinct book transactions to protect IP footprint
                if index < len(test_batch):
                    cooldown = random.uniform(3.0, 5.0)
                    print(f"⏳ [Cooldown] Waiting {cooldown:.2f}s before moving to next target book...")
                    await asyncio.sleep(cooldown)
                    
            print("\n🏁 Batch Run Complete! Review your terminal execution logs for filter confirmation.")
            
        except Exception as e:
            print(f"💥 [Critical Exception] Unexpected error caught inside orchestrator: {str(e)}")
            
        finally:
            # Guarantee resources clean up execution context regardless of loop breaks
            print("\n🔒 [Shutdown] Closing pipeline context safely.")
            await scraper.close_pipeline()

if __name__ == "__main__":
    asyncio.run(main())