# AI-Driven Short-Form Video Script Generation Pipeline

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask)
![LangChain](https://img.shields.io/badge/LangChain-008631?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)
![AWS Lambda](https://img.shields.io/badge/AWS%20Lambda-FF9900?style=for-the-badge&logo=aws-lambda)

## Overview

This repository contains the architecture for a sophisticated, AI-powered pipeline designed to automate the generation of high-quality, short-form video scripts from long-form content. The system ingests raw transcripts from sources like podcasts or interviews and produces multiple, distinct, and engaging video scripts ready for editing.

The service is built as a robust Flask application, containerized with Docker, and designed for scalable, serverless deployment on AWS Lambda.

---

## ⚠️ Portfolio Version Notice

**This is a sanitized, non-runnable version of a proprietary project developed during a professional internship.**

The core intellectual property, including all specific LLM prompts, proprietary evaluation rubrics, and the precise implementation details of the AI services, has been removed to respect confidentiality agreements.

The purpose of this repository is to showcase:
* **System Architecture:** The design of a multi-agent AI pipeline.
* **Code Quality:** Professional, clean, and well-documented code.
* **Production Readiness:** Best practices in configuration, deployment, and error handling.

---

## Key Features

* **Multi-Agent AI Architecture:** The pipeline is designed as a "digital assembly line" where each AI agent, powered by a Large Language Model (LLM), has a single, specialized role mimicking a professional creative team.
* **Dynamic, Per-Request LLM Configuration:** A flexible, three-tiered configuration system allows the client to specify the exact LLM provider and model for each individual service within a single API call, enabling fine-grained optimization for cost and performance.
* **Serverless-First Design:** The Flask application is fully containerized using a multi-stage `Dockerfile` and is production-ready for cost-effective, auto-scaling deployment on AWS Lambda.
* **Robust LLM Validation:** The pipeline includes defensive coding practices, such as a dedicated validation step to verify the output of LLM calls and protect against common failure modes like data hallucination.
* **Hybrid Indexing System:** A two-pass indexing system ensures script accuracy, first using a fast, deterministic offline algorithm to find script chunk locations, with a more powerful LLM-based "fuzzy search" serving as a fallback.

---

## The "Multi-Agent" Architecture

The system's core logic is a multi-agent pipeline where each step is handled by a specialized service. This modular, service-oriented design makes the system maintainable, testable, and easy to upgrade.

The flow is orchestrated by `pipeline_server.py` and proceeds as follows:

**1. The Pre-Processors (Data Foundation)**
* `IdMappingService`: Ingests the client's transcript and maps its arbitrary string IDs to clean, sequential integer indices for robust internal processing.
* `ChunkerService`: Divides the raw transcript into semantic "blocks" based on speaker turns and word count, creating contextually relevant chunks for AI analysis.

**2. The Producer (Concept Generation)**
* `LlmConceptGeneratorService`: Acts as the "Producer" by analyzing the transcript blocks to identify multiple, distinct "angles" or story ideas. Its key innovation is structuring each concept with a `title`, a `logline` (the core angle), and an inherent `narrative_structure` (e.g., "Problem -> Solution").

**3. The Story Editor (Content Selection)**
* `LlmConceptBlockMatcherService`: For each angle identified by the Producer, this service acts as the "Story Editor," selecting the most relevant and cohesive group of transcript blocks needed to tell that specific story.

**4. The Scriptwriter (Verbatim Scripting)**
* `LlmVerbatimScriptExtractorService`: This service writes the final script, operating under two strict, quality-enforcing constraints: it can **only use verbatim quotes** from the source blocks, and it must select them in their original **chronological order** to maintain narrative coherence.

**5. The Critic (Quality Evaluation)**
* `LlmScriptEvaluatorService`: The final creative agent, the Critic, acts as an unbiased quality checker. It evaluates the fully assembled script against a proprietary, multi-point rubric to assign a final score based on its potential for viewer engagement and virality.

---

## API Contract & Data Flow

The service is exposed via a single `/generate-shorts` endpoint. The client provides transcript data and can optionally override the model configuration for each service.

#### Example API Request

```json
{
  "service_configurations": {
    "llm_defaults": { "provider": "azure", "model": "o3" },
    "concept_generator": { "provider": "google", "model": "gemini-2.5-pro" },
    "script_evaluator": { "provider": "azure", "model": "gpt-4.1" }
  },
  "request_context": {
    "num_concepts_requested": 3
  },
  "elementsData": {
    "text": "The full transcript text...",
    "words": [
      {
        "text": "The", "start": 0.1, "end": 0.3, "type": "word", 
        "speaker_id": "speaker_0", "id": "client_id_123"
      }
    ]
  }
}
````

#### Example API Response

```json
{
  "status": "success",
  "results": [
    {
      "title": "The Secret to Starting Small",
      "title_id": "secret_to_starting_small",
      "logline": "The key to achieving big goals is to start with small, manageable steps.",
      "script": "The key is to start small. Don't try to build Rome in a day.",
      "status": "success",
      "duration_seconds": 4.8,
      "chunk_index_lists": [
        ["client_id_101", "client_id_102", "..."]
      ],
      "script_chunks": [
        {
          "chunk_text": "The key is to start small.",
          "start_word_index": "client_id_101",
          "end_word_index": "client_id_111"
        }
      ],
      "evaluation": {
        "overall_summary": "The script has a strong, clear hook and a satisfying payoff.",
        "overall_score": 4.8
      }
    }
  ]
}
```

-----

## Project Validation & Results

To validate the real-world effectiveness of the pipeline's output, an empirical test was conducted. Several long-form videos were processed by the system, and the top-rated generated scripts were manually edited into short-form videos. These were then uploaded to a brand-new YouTube channel with zero existing subscribers or audience history.

The results were highly successful. The content generated by the pipeline achieved an **average viewer retention rate of over 70%**. In the context of YouTube Shorts, a retention rate in the 70-80% range is a strong industry benchmark indicating highly engaging content that is likely to be promoted by the platform's algorithm. This result on a new channel demonstrated the pipeline's ability to successfully execute its core mission: to automatically identify and structure inherently compelling narratives that resonate with a cold audience.