from pathlib import Path

# =====================================================================
# 1. CONFIGURATION LAYER (Separation of Concerns: Constants Only)
# =====================================================================
class PipelineConfig:
    """Stores all immutable system variables, directory paths, and CSS selectors."""
    
    # Dynamic Absolute Path Resolution (Safe execution from any folder)
    ROOT_DIR = Path(__file__).resolve().parents[1]
    QUEUE_CSV_PATH = ROOT_DIR / "books_queue.csv"
    RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
    PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"

    # --- New Scope Constraints (Variable updates live here!) ---
    MAX_BOOKS_TO_PROCESS = 200      # Small test batch throttle variable
    TARGET_REVIEWS_PER_BOOK = 1000  # Exit criteria per book
    
    # Anti-Bot & Network Defense Settings
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Targeted Goodreads Elements   
    POPUP_CLOSE_SELECTOR = "div[role='dialog']:has-text('Sign up') .Overlay__close, div[role='dialog']:has-text('Sign in') .Overlay__close"
    
    # Strict Network Latency Guardrails (in Milliseconds)
    PRIMARY_TIMEOUT_MS = 60000  # 60 Seconds
    FALLBACK_TIMEOUT_MS = 90000 # 90 Seconds


# --- CSS Selectors for Filters Modal ---
    FILTER_BUTTON_SELECTOR = ".ReviewFilters button:has-text('Filters')"
    FILTERS_MODAL_SELECTOR = "div.Overlay__window, div[role='dialog']"
    
    # REFACTORED: Target the user-facing text labels inside the modal layout context
    RADIO_NEWEST_SELECTOR = ".Overlay__window label:has-text('Newest first'), .Overlay__window label:has(input[value='default'])"
    RADIO_THIS_EDITION_SELECTOR = ".Overlay__window label:has-text('Reviews of this edition'), .Overlay__window label:has(input[value='true'])"
    RADIO_ENGLISH_SELECTOR = ".Overlay__window label:has-text('English'), .Overlay__window label:has(input[value='en'])"
    
    # Robustly scope the action items within the overlay control wrapper
    APPLY_FILTERS_BUTTON_SELECTOR = ".Overlay__actions button:has-text('Apply'), .Overlay__footer button.Button--primary"


# --- NEW: Data Extraction Selectors (Reviews & Pagination) ---
    # =================================================================
    # Targets the outermost container for each individual review
    REVIEW_CARD_SELECTOR = "article.ReviewCard"
    
    # Scoped inside REVIEW_CARD_SELECTOR to find the reviewer's profile link
    REVIEWER_LINK_SELECTOR = "a[href*='/user/show/']"
    
    # Scoped inside REVIEW_CARD_SELECTOR to find the raw text container
    REVIEW_TEXT_SELECTOR = "section.ReviewText__content"
    
    # Targets the Next Page button within the reviews pagination block
    # Targets the "More reviews and ratings >" button based on exact aria-label from the DOM
    NEXT_PAGE_BUTTON_SELECTOR = "a[aria-label='Tap to show more reviews and ratings']"