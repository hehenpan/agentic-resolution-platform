import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src and repo root to sys.path to allow imports from agent and shared_common
test_data_dir = Path(__file__).resolve().parent
tests_dir = test_data_dir.parent
repo_root = tests_dir.parent.parent
ai_agent_src = tests_dir.parent / "src"

if str(ai_agent_src) not in sys.path:
    sys.path.insert(0, str(ai_agent_src))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Set test environment to load config.ini or config_dev.ini
os.environ["APP_ENV"] = "dev"

load_dotenv(dotenv_path=tests_dir.parent / ".env")

from agent.core.embedding import get_embedding_model  # noqa: E402
from agent.core.logger import logger  # noqa: E402

CACHE_FILE = str(test_data_dir / "query_embeddings_cache.json")

async def build_cache():
    logger.info(
        "[PRE-BUILD-CACHE] Loading query embeddings cache at: {}",
        CACHE_FILE,
    )
    
    # Load existing cache if exists
    cache_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            logger.info(
                "[PRE-BUILD-CACHE] Loaded {} existing cache entries.",
                len(cache_data),
            )
        except Exception as error:
            logger.warning(
                "[PRE-BUILD-CACHE] Could not load existing cache: {}",
                error,
            )

    embedding_model = get_embedding_model()

    queries_to_embed = [
        # Query 1
        "Each product page shows an estimated dispatch timeframe near the listed price. "
        "From when your items ship, products typically arrive within 1-2 working days for North Island deliveries "
        "and 2-3 working days for South Island deliveries. Rural deliveries may take an extra working day. "
        "Bulk & hazard deliveries may take an extra 2-7 working days and tracking links for these deliveries "
        "can take a few days to generate.",
        
        # Query 2 (New)
        "how many working days for products typically arrive for North Island?"
    ]

    updated = False
    for query in queries_to_embed:
        if query not in cache_data:
            logger.info(
                "[PRE-BUILD-CACHE] Generating embedding for: '{}'",
                query,
            )
            # Wait briefly to avoid 429
            await asyncio.sleep(0.65)
            vector = await embedding_model.aembed_query(query)
            cache_data[query] = vector
            updated = True
        else:
            logger.info(
                "[PRE-BUILD-CACHE] Query already cached: '{}...'",
                query[:30],
            )

    if updated or not os.path.exists(CACHE_FILE):
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        logger.info(
            "[PRE-BUILD-CACHE] Successfully wrote cache to {}",
            CACHE_FILE,
        )
    else:
        logger.info(
            "[PRE-BUILD-CACHE] Cache is already up to date. No write needed."
        )

if __name__ == "__main__":
    asyncio.run(build_cache())
