# src/services/output_formatter_service.py
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class OutputFormatterService:
    """
    Transforms internal pipeline results into the final client-facing format.

    This service is the final step in the pipeline. Its primary responsibility is
    to "rehydrate" the processed data, translating the clean, internal integer IDs
    used during processing back into the original, arbitrary string IDs provided
    by the client.
    """

    def __init__(self):
        """Initializes the output formatter service."""
        logger.info("OutputFormatterService initialized.")

    def run(self, pipeline_results: List[Dict], full_objects_transcript: Dict, id_map: Dict) -> List[Dict]:
        """
        Formats the final list of concepts into the desired output structure.

        Args:
            pipeline_results: The list of concept dictionaries after all processing.
            full_objects_transcript: The complete transcript containing all word,
                                     pause, and space objects with internal integer IDs.
            id_map: The mapping from internal integer IDs back to original client string IDs.

        Returns:
            A list of formatted, client-ready concept dictionaries.
        """
        client_results = []
        for concept in pipeline_results:
            # Pass through any concepts that errored during the pipeline.
            if concept.get('status') == 'error':
                client_results.append({
                    "title": concept.get('title'),
                    "title_id": concept.get('title_id'),
                    "logline": concept.get('logline'),
                    "status": "error",
                    "error_message": concept.get('error_message', 'An unknown error occurred.')
                })
                continue
            
            formatted_concept = self._format_single_concept(concept, full_objects_transcript, id_map)
            client_results.append(formatted_concept)
            
        return client_results

    def _format_single_concept(self, concept: Dict, full_objects_transcript: Dict, id_map: Dict) -> Dict:
        """Formats one concept, remapping internal IDs back to client IDs."""
        all_objects_list = full_objects_transcript.get('words', [])
        # Create a lookup for O(1) access to an object's position by its internal ID.
        id_to_position_map = {obj['id']: i for i, obj in enumerate(all_objects_list)}

        total_duration = 0.0
        chunk_index_lists = []
        remapped_script_chunks = []

        for chunk in concept.get('script_chunks', []):
            start_word_id = chunk.get('start_word_index')  # Internal integer ID
            end_word_id = chunk.get('end_word_index')      # Internal integer ID

            if start_word_id is None or end_word_id is None:
                continue

            # Step 1: Find the list positions of the start and end words.
            start_pos = id_to_position_map.get(start_word_id)
            end_pos = id_to_position_map.get(end_word_id)

            if start_pos is None or end_pos is None:
                continue

            # Step 2: Slice the full transcript to get every object (words, spaces) in the chunk.
            full_slice = all_objects_list[start_pos : end_pos + 1]
            if not full_slice:
                continue
            
            # Step 3: Remap the internal IDs back to the original client string IDs.
            remapped_ids = [id_map.get(obj['id']) for obj in full_slice if obj['id'] in id_map]
            chunk_index_lists.append([rid for rid in remapped_ids if rid is not None])

            # Step 4: Calculate duration and format the chunk for the client output.
            total_duration += (full_slice[-1]['end'] - full_slice[0]['start'])
            remapped_script_chunks.append({
                "chunk_text": chunk.get('chunk_text'),
                "start_word_index": id_map.get(start_word_id),
                "end_word_index": id_map.get(end_word_id)
            })

        return {
            "title": concept.get('title'),
            "title_id": concept.get('title_id'),
            "logline": concept.get('logline'),
            "script": concept.get('script'),
            "status": "success",
            "duration_seconds": round(total_duration, 2),
            "chunk_index_lists": chunk_index_lists,
            "script_chunks": remapped_script_chunks,
            "evaluation": concept.get('evaluation'),
            "recommendations": concept.get('recommendations')
        }
