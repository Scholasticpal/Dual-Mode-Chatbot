"""Ingests PDF documents and CSV order data into Supabase."""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pypdf import PdfReader
from supabase import Client, create_client

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent / "data"
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
ORDERS_BATCH_SIZE = 50

ORDERS_COLUMN_MAP: dict[str, str] = {
    "order_id": "order_id",
    "customer": "customer",
    "product": "product",
    "amount": "amount",
    "status": "status",
    "order_date": "order_date",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingest")


def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        raise EnvironmentError("Missing GEMINI_API_KEY")
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key,
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )


def _get_db() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set.")
        raise EnvironmentError("Missing Supabase credentials")
    return create_client(url, key)


def _read_pdf_files(directory: Path) -> list[tuple[str, list[str]]]:
    """Extracts non-empty text chunks from PDF files in the specified directory."""
    results: list[tuple[str, list[str]]] = []
    pdf_files = sorted(directory.glob("*.pdf"))

    if not pdf_files:
        logger.warning("No .pdf files found in %s", directory)
        return results

    for filepath in pdf_files:
        try:
            reader = PdfReader(filepath)
        except Exception:
            logger.exception("Failed to open '%s'.", filepath.name)
            continue

        page_texts = [page.extract_text() for page in reader.pages if page.extract_text()]
        raw = "\n\n".join(page_texts)
        chunks = [chunk.strip() for chunk in raw.split("\n\n") if chunk.strip()]
        results.append((filepath.name, chunks))
        logger.info("Read '%s' (%d page(s)) — %d section(s) extracted.", filepath.name, len(reader.pages), len(chunks))

    return results


def _embed_texts(embeddings: GoogleGenerativeAIEmbeddings, texts: list[str]) -> list[list[float]]:
    return embeddings.embed_documents(texts)


def ingest_documents() -> None:
    """Ingests PDF documents into the document_sections table."""
    logger.info("Starting document ingestion.")

    file_chunks = _read_pdf_files(DATA_DIR)
    if not file_chunks:
        return

    embeddings = _get_embeddings()
    db = _get_db()

    total_sections = 0
    start = time.perf_counter()

    for filename, chunks in file_chunks:
        if not chunks:
            continue

        logger.info("Embedding %d section(s) from '%s'...", len(chunks), filename)

        try:
            embedded_chunks = _embed_texts(embeddings, chunks)
        except Exception:
            logger.exception("Failed to embed sections from '%s'.", filename)
            continue

        rows = [
            {"content": chunk, "embedding": embedding, "source_doc": filename}
            for chunk, embedding in zip(chunks, embedded_chunks)
        ]

        try:
            db.table("document_sections").insert(rows).execute()
            total_sections += len(rows)
            logger.info("Inserted %d section(s) from '%s'.", len(rows), filename)
        except Exception:
            logger.exception("Insert failed for '%s'.", filename)
            continue

    logger.info(
        "Document ingestion complete — %d total section(s) in %.2f s.", total_sections, time.perf_counter() - start
    )


def _normalise_date(value: str) -> str:
    """Converts a date string to ISO 8601 (YYYY-MM-DD)."""
    value = value.strip()

    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        pass

    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    logger.warning("Could not parse date '%s' — inserting as-is.", value)
    return value


def _load_orders(csv_path: Path) -> list[dict[str, Any]]:
    """Loads and sanitises orders from CSV."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {csv_path}")

    rows = []

    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        if reader.fieldnames is None:
            raise ValueError("CSV header missing")

        col_map = {col: col.strip().lower() for col in reader.fieldnames}

        for idx, raw_row in enumerate(reader, start=1):
            row = {}
            for original_col, normalised_col in col_map.items():
                value = raw_row[original_col].strip()

                if normalised_col == "amount":
                    try:
                        value = float(value)
                    except ValueError:
                        logger.warning("Row %d: non-numeric amount '%s'", idx, value)
                elif normalised_col == "order_date":
                    value = _normalise_date(value)

                row[normalised_col] = value

            rows.append(row)

    logger.info("Loaded %d order row(s) from '%s'.", len(rows), csv_path.name)
    return rows


def _chunked(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def ingest_orders() -> None:
    """Ingests orders from CSV into the orders table in batches."""
    logger.info("Starting orders ingestion.")

    csv_path = DATA_DIR / "orders.csv"
    orders = _load_orders(csv_path)

    if not orders:
        return

    db = _get_db()

    total_inserted = 0
    start = time.perf_counter()
    chunks = list(_chunked(orders, ORDERS_BATCH_SIZE))

    for chunk_idx, chunk in enumerate(chunks, start=1):
        try:
            db.table("orders").insert(chunk).execute()
            total_inserted += len(chunk)
            logger.info("Chunk %d/%d — inserted %d row(s).", chunk_idx, len(chunks), len(chunk))
        except Exception:
            logger.exception("Chunk %d/%d failed.", chunk_idx, len(chunks))

    logger.info(
        "Orders ingestion complete — %d row(s) inserted in %.2f s.", total_inserted, time.perf_counter() - start
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents and orders into Supabase.")
    parser.add_argument("--docs", action="store_true", help="Ingest .pdf documents only.")
    parser.add_argument("--orders", action="store_true", help="Ingest orders.csv only.")
    args = parser.parse_args()

    run_docs = args.docs or not (args.docs or args.orders)
    run_orders = args.orders or not (args.docs or args.orders)

    if run_docs:
        ingest_documents()

    if run_orders:
        ingest_orders()


if __name__ == "__main__":
    main()
