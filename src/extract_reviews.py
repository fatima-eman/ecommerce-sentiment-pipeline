import os
import csv
import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError

# =====================================================================
# 1. CONFIGURATION LAYER (Separation of Concerns: Constants Only)
# =====================================================================
class PipelineConfig:
    """Stores all immutable system variables, directory paths, and CSS selectors."""
    
    # Dynamic Absolute Path Resolution (Safe execution from any folder)
    ROOT_DIR = Path(__file__).resolve().parents[1]
    QUEUE_CSV_PATH = ROOT_DIR / "books_queue.csv"
    RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
    
    # Anti-Bot & Network Defense Settings
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Targeted Goodreads Elements
    POPUP_CLOSE_SELECTOR = ".Overlay__close"
    
    # Strict Network Latency Guardrails (in Milliseconds)
    PRIMARY_TIMEOUT_MS = 60000  # 60 Seconds
    FALLBACK_TIMEOUT_MS = 90000 # 90 Seconds


# =====================================================================
# 2. JOB QUEUE CONTROLLER (Your Validated Queue Logic)
# =====================================================================
def get_pending_books(queue_file: Path) -> list:
    """Reads the centralized tracking queue and extracts all pending operations."""
    pending_books = []
    if not queue_file.exists():
        print(f"❌ [Queue Error] File not found at: {queue_file}. Run Phase 1 first!")
        return pending_books

    with open(queue_file, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Enforce Case Insensitivity comparison for robustness
            if row.get("Status", "").strip().lower() == "pending":
                pending_books.append(row)
        print(f"📊 [Queue Status] Found {len(pending_books)} pending books.")
    return pending_books


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

    async def initialize_pipeline(self, playwright_instance) -> None:
        """Launches the sandboxed browser environment and configures human traits."""
        print("🌐 Launching automated browser instance...")
        
        # Headless=False allows you to visually audit your defenses during runtime
        self.browser = await playwright_instance.chromium.launch(headless=False)
        
        # Inject standard human fingerprint (User Agent) to clear low-level firewalls
        self.context = await self.browser.new_context(user_agent=self.config.USER_AGENT)
        self.page = await self.context.new_page()
        
        # IMMEDIATELY arm the pop-up defense system right after launching the page
        await self._register_popup_defense()

    async def _register_popup_defense(self) -> None:
        """Registers a low-level asynchronous listener in Playwright's engine.

        Fires automatically whenever the sign-up modal blocks the screen.
        """
        popup_locator = self.page.locator(self.config.POPUP_CLOSE_SELECTOR)
        
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

    async def close_pipeline(self) -> None:
        """Safely deallocates browser memory buffers and stops all threads."""
        if self.browser:
            print("\n🛑 Shutting down browser resources and safely closing down connection channels.")
            await self.browser.close()


# =====================================================================
# 4. COORDINATION & ORCHESTRATION LAYER (The Conductor Loop)
# =====================================================================
async def main():
    # Instantiate immutable configuration settings
    config = PipelineConfig()
    
    print("📋 Initializing Job Queue Verification...")
    queue = get_pending_books(config.QUEUE_CSV_PATH)
    print(f"📊 Tracking Dataset Results: Detected {len(queue)} books waiting in 'Pending' state.")
    
    if not queue:
        print("⚠️  No pending operations inside queue. Pipeline execution aborted.")
        return
        
    # Extract the absolute first record to test our navigation & defense layers cleanly
    sample_book = queue[0]
    sample_title = sample_book.get("Book Title", "").strip()
    sample_url = sample_book.get("URL", "").strip()
    
    print(f"\n🎯 [Target Acquired] Preparing evaluation run for: '{sample_title}'")
    
    # Initialize Context-Managed Async Playwright Engine
    async with async_playwright() as p:
        scraper = GoodreadsScraper(config)
        await scraper.initialize_pipeline(p)
        
        # Test navigation runtime, error handlings, and interceptor status
        success = await scraper.navigate_to_book(sample_url)
        
        if success:
            print("\n🏁 Validation Success! Your initialization, defense, and navigation blocks are rock-solid.")
        else:
            print("\n❌ Validation Failed! Review your internet connectivity or selector health.")
            
        await scraper.close_pipeline()

if __name__ == "__main__":
    asyncio.run(main())