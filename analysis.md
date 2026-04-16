# Ironclad-OCR Project Analysis

## Overview
Ironclad-OCR is an application designed to process PDF invoices from vendors using OCR (Optical Character Recognition) and AI models. It uses FastAPI for the API, Redis for queueing, Supabase for PostgreSQL database and storage, and LangGraph for managing the extraction workflow. The core functionality centers around extracting structured data from vendor invoices using Gemini models.

## Architecture

### 1. API (`src/api`)
The FastAPI application provides three main endpoints:
- `POST /ingest`: Uploads a PDF file, saves it to disk, creates a job record in Supabase, and enqueues a job in Redis.
- `GET /jobs/{job_id}`: Retrieves the status of a specific processing job from Supabase.
- `POST /approve`: Receives user approval for a proposed schema for a vendor, updates the registry, and requeues the job.
- `GET /health`: Checks the health of Redis and Supabase.

### 2. Worker (`src/worker`)
A standalone Python worker process (`worker.py`) that reads messages from the Redis queue. For each message, it executes a LangGraph workflow (`_process_message`) to handle the PDF document.

### 3. Core Logic & AI (`src/core`)
- **LangGraph Workflow (`graph.py`)**: Defines the state machine for processing a document:
  1. `fingerprint_and_lookup`: Identifies the vendor and header text using Gemini, computes a fingerprint, and looks up the vendor in Supabase.
  2. `discovery_agent`: If the vendor is new, uses Gemini to infer a schema.
  3. `schema_evolution_agent`: If the vendor layout drifted, proposes an updated schema using Gemini.
  4. `human_hold`: Pauses the workflow waiting for a human to approve the proposed schema.
  5. `extract`: Extracts the fields from the invoice based on the approved schema using Gemini.
  6. `deliver_webhook`: Sends the final extracted data to an external webhook.
- **AI Nodes (`nodes.py`)**: Uses the Google Gemini API (`google-genai` library) to interact with LLMs. Models used include `gemini-3-flash-preview`, `gemini-2.0-flash`, and `gemini-2.0-flash-lite`. It includes rate limiting and retry logic for the Gemini API.

### 4. Infrastructure (`src/infrastructure`)
- **Redis Queue (`redis_queue.py`)**: Handles the asynchronous queueing of jobs.
- **Supabase Repositories (`supabase_repos.py`)**: Manages interactions with Supabase:
  - `SupabaseRegistryRepository`: Manages the `document_registry` table (vendor schemas).
  - `SupabaseJobsRepository`: Manages the `processing_jobs` table (job state tracking).
- **Webhook Client (`webhook_client.py`)**: Handles delivering the final extracted payload.

## Technologies Used
- **Python 3.11/3.12**
- **FastAPI / Uvicorn** for the web API
- **Redis** for asynchronous message queueing
- **Supabase** as the database (PostgreSQL)
- **LangGraph** to build the agent workflow
- **Google GenAI (Gemini)** for text extraction and schema discovery
- **pdf2image & poppler** for converting PDFs to images
- **Pydantic** for schema validation and dynamic model creation
- **Pytest** for testing

## Docker Environment
The project is containerized using Docker, with a `docker-compose.yml` defining an API service, a worker service, and a Redis instance. Both services require environment variables like `GOOGLE_API_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`.

## Tests
A test suite is available under `tests/` and uses `pytest` and `pytest-asyncio`. The tests currently pass when dependencies are properly installed.