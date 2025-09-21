# src/services/llm_concept_block_matcher_service.py

# Note: The core LLM prompt and calling logic have been removed to protect
# proprietary intellectual property. The validation logic has been preserved
# to demonstrate robust, production-ready coding practices.

import logging
from typing import List, Dict

from ..utils.llm_handler import LlmApiHandler

logger = logging.getLogger(__name__)


class LlmConceptBlockMatcherService:
    """
    Identifies and validates transcript blocks relevant to a specific video concept.

    This service acts as the "Story Editor" in the pipeline. For each creative
    concept, it performs a two-step process:
    1.  Uses an LLM to perform a semantic search and identify a cohesive group
        of candidate blocks from the full transcript.
    2.  Rigorously validates the LLM's output to guard against common issues
        like hallucinated block IDs or mismatched content.
    """

    def __init__(self):
        """Initializes the block matcher service."""
        logger.info("LlmConceptBlockMatcherService initialized.")

    def run(self, concepts_data: List[Dict], blocks_data: List[Dict], llm_handler: LlmApiHandler) -> List[Dict]:
        """
        Processes each concept to find and validate relevant transcript blocks.

        Args:
            concepts_data: A list of concept dictionaries to be processed.
            blocks_data: A list of all available transcript blocks.
            llm_handler: An instance of the LLM handler for API communication.

        Returns:
            The list of concepts, augmented with a 'matched_blocks' key containing
            a list of validated block matches.
        """
        block_lookup = {b['block_id']: b for b in blocks_data}
        augmented_concepts = []

        for concept in concepts_data:
            logger.info(f"Finding matches for concept: \"{concept['title']}\"")
            try:
                # In the original implementation, an LLM is called. Here, we use
                # a mock response to demonstrate the subsequent validation logic.
                mock_llm_matches = self._get_mock_llm_response(block_lookup)

                # This validation logic is a key feature and is preserved to show
                # how the system ensures the reliability of the LLM's output.
                validated_matches = self._get_validated_matches(mock_llm_matches, block_lookup)

                # Calculate total duration of only the successfully validated blocks.
                total_duration = sum(
                    block_lookup[match['block_id']]['end_time'] - block_lookup[match['block_id']]['start_time']
                    for match in validated_matches if match['is_validated']
                )
                concept['matched_blocks'] = validated_matches
                concept['matched_blocks_total_duration'] = total_duration
                augmented_concepts.append(concept)

            except Exception as e:
                logger.error(f"Could not process concept '{concept['title_id']}': {e}")
                concept['matched_blocks'] = []
                concept['matched_blocks_total_duration'] = 0.0
                augmented_concepts.append(concept)
        
        return augmented_concepts

    def _get_validated_matches(self, llm_matches: List[Dict], block_lookup: Dict) -> List[Dict]:
        """
        Performs a verification loop on the LLM's suggested block matches.

        This method is crucial for ensuring pipeline reliability. It checks for
        two common LLM failure modes:
        1.  **ID Hallucination**: Verifies that the `block_id` from the LLM
            actually exists in the source transcript.
        2.  **Content Mismatch**: Verifies that the `block_preview` from the LLM
            matches the start of the actual block text.
        """
        processed_matches = []
        if not llm_matches:
            return []

        for match in llm_matches:
            block_id = match.get("block_id")
            preview = match.get("block_preview")
            is_validated = False

            if block_id in block_lookup:
                actual_text = block_lookup[block_id]['text']
                if actual_text.strip().startswith(preview.strip()):
                    is_validated = True
                else:
                    logger.warning(f"Validation failed for '{block_id}': Preview '{preview}' did not match.")
            else:
                logger.warning(f"Validation failed: LLM hallucinated non-existent block_id '{block_id}'.")
            
            processed_matches.append({
                "block_id": block_id,
                "block_preview": preview,
                "is_validated": is_validated
            })
        
        return processed_matches

    def _get_mock_llm_response(self, block_lookup: Dict) -> List[Dict]:
        """
        Generates a mock LLM response to demonstrate the validation logic.

        This function simulates the output of the proprietary LLM call,
        including common failure cases that the validation step is designed to catch.
        """
        # If there are no blocks, return an empty list.
        if not block_lookup:
            return []
        
        # Select a valid block from the lookup to use as a correct match.
        valid_block_id = next(iter(block_lookup))
        valid_block_text = block_lookup[valid_block_id]['text']
        valid_preview = " ".join(valid_block_text.strip().split()[:3])

        # Simulate a response that includes one valid match, one with a bad preview,
        # and one with a hallucinated (non-existent) block_id.
        mock_response = [
            {"block_id": valid_block_id, "block_preview": valid_preview},
            {"block_id": valid_block_id, "block_preview": "This preview is wrong"},
            {"block_id": "block_999", "block_preview": "This ID does not exist"}
        ]
        logger.info("Generated mock LLM response for demonstration purposes.")
        return mock_response
