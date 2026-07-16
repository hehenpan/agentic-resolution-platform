import os
import sys
import json
import asyncio
import random
import time
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_text_splitters import MarkdownTextSplitter

# Add src and repo root to sys.path to allow imports from agent and shared_common
tests_dir = Path(__file__).resolve().parent.parent
repo_root = tests_dir.parent.parent
ai_agent_src = tests_dir.parent / "src"

if str(ai_agent_src) not in sys.path:
    sys.path.insert(0, str(ai_agent_src))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Set test environment to load config.ini or config_dev.ini
os.environ["APP_ENV"] = "dev"

from dotenv import load_dotenv
load_dotenv(dotenv_path=tests_dir.parent / ".env")

from agent.core.embedding import get_embedding_model
from agent.core.constants import GEMINI_EMBEDDING_DIM, QDRANT_COLLECTION_RAG
from agent.core.vectordb import RAGFileVectorPayload

DB_PATH = str(tests_dir / "test_data" / "qdrant_prebuilt_db")
CACHE_FILE = str(tests_dir / "test_data" / "query_embeddings_cache.json")
RAG_CORPUS_DIR = repo_root / "resource" / "rag_corpus"

async def build_database():
    print(f"[PRE-BUILD] Initializing Qdrant Client at persistent path: {DB_PATH}")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    client = QdrantClient(path=DB_PATH)

    # Recreate the collection to ensure a clean state
    if client.collection_exists(QDRANT_COLLECTION_RAG):
        print(f"[PRE-BUILD] Collection '{QDRANT_COLLECTION_RAG}' already exists. Recreating it...")
        client.delete_collection(QDRANT_COLLECTION_RAG)

    client.create_collection(
        collection_name=QDRANT_COLLECTION_RAG,
        vectors_config=VectorParams(size=GEMINI_EMBEDDING_DIM, distance=Distance.COSINE),
    )

    embedding_model = get_embedding_model()
    points = []

    # Specify exactly the 2 target file paths to process
    target_files = [
        RAG_CORPUS_DIR / "ecommerce" / "shipping_delivery_freight" / "general_ecommerce_delivery_rates_times_options.md",
        RAG_CORPUS_DIR / "ecommerce" / "privacy_terms" / "general_ecommerce_terms_and_conditions.md"
    ]
    
    # Initialize MarkdownTextSplitter
    splitter = MarkdownTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len
    )
    
    # Pre-parse files to calculate total chunks for progress estimation
    files_to_process = []
    total_chunks = 0
    
    for file_path in target_files:
        if not file_path.exists():
            print(f"[PRE-BUILD] Error: Target file not found at: {file_path}")
            sys.exit(1)
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Strip YAML frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
                
        chunks = splitter.split_text(content)
        # Filter out empty or very short noise
        chunks = [c.strip() for c in chunks if len(c.strip()) >= 10]
        files_to_process.append((file_path.name, file_path, chunks))
        total_chunks += len(chunks)

    print(f"[PRE-BUILD] Found {len(files_to_process)} target files with total of {total_chunks} chunks to embed.")

    processed_chunks = 0
    start_time = time.time()

    for file_name, file_path, chunks in files_to_process:
        print(f"\n[PRE-BUILD] Ingesting file: {file_name} ({len(chunks)} chunks)")
        
        for idx, chunk in enumerate(chunks):
            processed_chunks += 1
            progress_pct = (processed_chunks / total_chunks) * 100
            elapsed = time.time() - start_time
            est_total = (elapsed / processed_chunks) * total_chunks if processed_chunks > 0 else 0
            est_remaining = est_total - elapsed
            
            print(
                f"[PRE-BUILD] [{progress_pct:6.2f}%] Embedding chunk {idx+1}/{len(chunks)} of '{file_name}' "
                f"(Total: {processed_chunks}/{total_chunks}). "
                f"Elapsed: {elapsed:.1f}s, Est. remaining: {est_remaining:.1f}s"
            )

            # Delay to avoid 429 rate limits
            await asyncio.sleep(0.65)
            vector = await embedding_model.aembed_query(chunk)

            # Randomize IDs as per requirement
            rand_file_id = random.randint(1000, 9999)
            rand_owner_id = random.randint(100, 999)
            
            # Instantiating RAGFileVectorPayload to align exactly with store_in_vector_db schema
            payload = RAGFileVectorPayload(
                file_id=rand_file_id,
                file_name=file_name,
                file_size=len(chunk.encode("utf-8")),
                file_owner_id=rand_owner_id,
                file_tenant_id=1,
                text=chunk,
                extra_meta={},
                extra_context={}
            )

            points.append(
                PointStruct(
                    id=rand_file_id,
                    vector=vector,
                    payload=payload.model_dump()
                )
            )

    print(f"\n[PRE-BUILD] Upserting {len(points)} points into Qdrant collection '{QDRANT_COLLECTION_RAG}'")
    client.upsert(
        collection_name=QDRANT_COLLECTION_RAG,
        points=points
    )
    print("[PRE-BUILD] Database built successfully.")

if __name__ == "__main__":
    asyncio.run(build_database())
