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

    # --- New Scope Constraints (Variable updates live here!) ---
    MAX_BOOKS_TO_PROCESS = 3       # Small test batch throttle variable
    TARGET_REVIEWS_PER_BOOK = 100  # Exit criteria per book

    # REFACTOR: Look for the 'Filters' button context directly inside the ReviewFilters block
    # This completely ignores whether intermediate parent divs change classes or layouts!
    FILTER_BUTTON_SELECTOR = ".ReviewFilters button:has-text('Filters')"
    
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