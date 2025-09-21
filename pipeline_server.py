# pipeline_server.py

# This file serves as the main entry point and orchestrator for the AI script
# generation pipeline. It defines the Flask web server, manages service
# instantiation, and controls the flow of data through the multi-step process.

import uuid
import flask
import logging
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor

# --- Core Application Imports ---
# In this public version of the repository, the implementation details of the
# LLM-based services have been abstracted away to protect intellectual property.
# The class structures are preserved to demonstrate the overall architecture.
from src.utils.config_loader import load_config
from src.utils.llm_handler import LlmApiHandler
from src.services.id_mapping_service import IdMappingService
from src.services.chunker_service import ChunkerService
from src.services.llm_summarizer_service import LlmSummarizerService
from src.services.llm_concept_generator_service import LlmConceptGeneratorService
from src.services.llm_concept_block_matcher_service import LlmConceptBlockMatcherService
from src.services.llm_verbatim_script_extractor_service import LlmVerbatimScriptExtractorService
from src.services.offline_indexer_service import OfflineIndexerService
from src.services.llm_verbatim_indexer_service import LlmVerbatimIndexerService
from src.services.llm_script_evaluator_service import LlmScriptEvaluatorService
from src.services.output_formatter_service import OutputFormatterService

# --- App and Logging Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)  # Quieten noisy third-party logger
app = flask.Flask(__name__)

# --- Global Config and Service Instantiation ---
try:
    CONFIG = load_config()
    app.logger.info("Configuration loaded successfully.")
except Exception as e:
    app.logger.error(f"CRITICAL: Could not load configuration. Server cannot start. Error: {e}")
    CONFIG = None

# Instantiate all services that comprise the pipeline.
id_mapping_service = IdMappingService()
chunker_service = ChunkerService(CONFIG.get('chunker', {}))
summarizer_service = LlmSummarizerService()
concept_generator_service = LlmConceptGeneratorService()
matcher_service = LlmConceptBlockMatcherService()
script_extractor_service = LlmVerbatimScriptExtractorService()
offline_indexer_service = OfflineIndexerService()
llm_indexer_service = LlmVerbatimIndexerService()
evaluator_service = LlmScriptEvaluatorService()
output_formatter_service = OutputFormatterService()


def process_single_concept(
    concept: Dict,
    blocks_data: List[Dict],
    long_form_summary: str,
    handlers: Dict[str, LlmApiHandler],
    request_id: str
) -> Dict:
    """
    Worker function to process one concept through the parallel part of the pipeline.

    This function is executed by the ThreadPoolExecutor for each generated concept,
    allowing multiple concepts to be scripted and evaluated simultaneously.
    """
    title_id = concept.get('title_id', 'unknown_concept')
    log_prefix = f"[{request_id}][{title_id}]"
    app.logger.info(f"{log_prefix} Starting parallel processing for concept.")

    try:
        # Step 5a: Match concept to relevant transcript blocks.
        matched_concept = matcher_service.run([concept], blocks_data, handlers['concept_block_matcher'])[0]
        # Step 5b: Extract a verbatim script from the matched blocks.
        scripted_concept = script_extractor_service.run([matched_concept], blocks_data, handlers['verbatim_script_extractor'])[0]
        # Step 5c: Perform a fast, offline search to find word indices for the script.
        indexed_concept = offline_indexer_service.run([scripted_concept], blocks_data)[0]
        
        # Step 5d: For any failed chunks, use a powerful LLM-based fallback indexer.
        if any('start_word_index' not in chunk for chunk in indexed_concept.get('script_chunks', [])):
            indexed_concept = llm_indexer_service.run([indexed_concept], blocks_data, handlers['verbatim_indexer'])[0]

        # Step 5e: Evaluate the final script against a proprietary rubric.
        script_text = indexed_concept.get('script', '')
        if script_text:
            evaluation = evaluator_service.run(script_text, long_form_summary, handlers['script_evaluator'])
            indexed_concept['evaluation'] = evaluation if evaluation else None

        indexed_concept['status'] = 'success'
        app.logger.info(f"{log_prefix} Successfully processed concept.")
        return indexed_concept

    except Exception as e:
        app.logger.error(f"{log_prefix} Error processing concept: {e}", exc_info=True)
        concept['status'] = 'error'
        concept['error_message'] = str(e)
        return concept


@app.route('/generate-shorts', methods=['POST'])
def generate_shorts():
    """
    Main API endpoint to generate short-form video scripts from a transcript.
    This function orchestrates the entire sequential and parallel pipeline.
    """
    request_id = str(uuid.uuid4())[:8]
    app.logger.info(f"[{request_id}] Received new request.")

    if CONFIG is None:
        return flask.jsonify({"error_message": "Server configuration error."}), 500
    if not flask.request.is_json:
        return flask.jsonify({"error_message": "Request must be JSON."}), 400

    try:
        request_data = flask.request.get_json()
        if not request_data.get('elementsData'):
            return flask.jsonify({"error_message": "Missing 'elementsData' in request."}), 400

        # --- Pipeline Stage 1: Pre-processing ---
        textual_transcript, full_objects_transcript, id_map = id_mapping_service.run(request_data['elementsData'])
        blocks_data = chunker_service.run(textual_transcript)

        # --- Pipeline Stage 2: Dynamic Handler and Concept Generation ---
        # Create LLM handlers dynamically based on per-request configurations,
        # demonstrating a highly flexible, client-driven architecture.
        global_llm_config = CONFIG.get('llm', {})
        service_configs = request_data.get('service_configurations', {})
        handlers = {
            name: LlmApiHandler({**global_llm_config.get(s_conf['provider'], {}), **s_conf})
            for name, s_conf in service_configs.items()
        }
        
        full_transcript_text = "".join([w['text'] for w in textual_transcript.get("words", [])])
        long_form_summary = summarizer_service.run(full_transcript_text, handlers['summarizer'])
        
        # Dynamically determine the optimal number of concepts to generate.
        num_concepts_requested = request_data.get('request_context', {}).get('num_concepts_requested', 4)

        concepts = concept_generator_service.run(blocks_data, handlers['concept_generator'], num_concepts_requested)
        if not concepts:
            return flask.jsonify({"status": "success", "results": []}), 200

        # --- Pipeline Stage 3: Parallel Processing ---
        # Use a thread pool to process each concept independently and concurrently,
        # dramatically improving throughput for multi-concept requests.
        final_results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_single_concept, c, blocks_data, long_form_summary, handlers, request_id) for c in concepts]
            for future in futures:
                final_results.append(future.result())

        # --- Pipeline Stage 4: Final Formatting ---
        client_output = output_formatter_service.run(final_results, full_objects_transcript, id_map)
        
        app.logger.info(f"[{request_id}] Successfully processed request.")
        return flask.jsonify({"status": "success", "results": client_output}), 200

    except Exception as e:
        app.logger.error(f"[{request_id}] An unexpected error occurred: {e}", exc_info=True)
        return flask.jsonify({"error_message": "An unexpected server error occurred."}), 500


if __name__ == '__main__':
    if CONFIG:
        app.run(host='0.0.0.0', port=5000, debug=False)
