#!/usr/bin/env python3
"""Create a serverless Vertex AI RAG corpus for NextBinge and index the entertainment guide."""

import sys
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr
import vertexai

PROJECT_ID = "qwiklabs-gcp-03-f18f2b72d55a"
LOCATION   = "us-central1"                             # Serverless RAG mode is us-central1 only
GCS_PATH   = "gs://nextbinge-media/rag/entertainment_guide.txt"

print(f"Initializing Vertex AI for project={PROJECT_ID}, location={LOCATION}...")
vertexai.init(project=PROJECT_ID, location=LOCATION)

# 1. Switch the region's RAG managed DB to serverless mode (project-level, once).
cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
print("Configuring RAG managed DB to serverless mode...")
try:
    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=cfg,
            rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
        )
    )
    print("✓ RAG engine configured to serverless mode.")
except Exception as e:
    print(f"Note on ragEngineConfig update: {e}")

# 2. Create the corpus.
print("Creating RAG corpus 'nextbinge-entertainment-guide'...")
corpus = rag.create_corpus(
    display_name="nextbinge-entertainment-guide",
    embedding_model_config=rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-005"
    ),
)
corpus_name = corpus.name
print(f"✓ Corpus created successfully: {corpus_name}")

# 3. Import + parse + chunk + embed.
PARSING_PROMPT = (
    "Extract the individual useful facts, thematic analyses, lore, character dynamics, "
    "and episode explanations described in this entertainment guide. "
    "Ignore and omit any boilerplate. "
    "Output clean, self-contained prose."
)

print(f"Importing files from {GCS_PATH} into corpus...")
try:
    resp = rag.import_files(
        corpus_name=corpus_name,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        llm_parser=rag.LlmParserConfig(
            model_name="gemini-1.5-flash",
            custom_parsing_prompt=PARSING_PROMPT,
        ),
    )
    print(f"✓ Imported {resp.imported_rag_files_count} file(s) with LLM parser.")
except Exception as e:
    print(f"LLM parser encountered: {e}. Retrying with default chunk parser...")
    resp = rag.import_files(
        corpus_name=corpus_name,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
    )
    print(f"✓ Imported {resp.imported_rag_files_count} file(s) with standard parser.")

print(f"\nSUCCESS! RAG Corpus Resource Name:\n{corpus_name}")
