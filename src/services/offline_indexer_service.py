# src/services/offline_indexer_service.py
import logging
from typing import List, Dict, Optional

from ..utils.exact_sequence_matcher import ExactSequenceMatcher
from ..utils.text_utils import normalize_word

logger = logging.getLogger(__name__)


class OfflineIndexerService:
    """
    Finds start/end word indices for script chunks using a deterministic algorithm.

    This service performs a fast, "offline" (non-LLM) search to locate the
    precise position of each script chunk within its original source block. It serves
    as the primary, efficient method for indexing, with an LLM-based indexer
    acting as a fallback for any chunks that fail this process.
    """

    def __init__(self):
        """Initializes the OfflineIndexerService and its sequence matcher utility."""
        logger.info("OfflineIndexerService initialized.")
        # This service delegates the core matching logic to a specialized utility.
        self.matcher = ExactSequenceMatcher()

    def run(self, scripts_data: List[Dict], blocks_data: List[Dict]) -> List[Dict]:
        """
        Iterates through script chunks and attempts to find their word indices.

        Args:
            scripts_data: The list of concept objects, each containing script chunks.
            blocks_data: The list of all block objects with word-level data.

        Returns:
            The list of concepts, with indices added to the script chunks where found.
        """
        block_lookup = {b['block_id']: b for b in blocks_data}
        
        for concept in scripts_data:
            title = concept.get('title', 'N/A')
            logger.info(f"Performing offline indexing for concept: \"{title}\"")
            
            processed_chunks = []
            for chunk in concept.get('script_chunks', []):
                try:
                    # Attempt to find the start and end indices for the chunk.
                    indices = self._find_indices_for_chunk(chunk, block_lookup)
                    if indices:
                        chunk.update(indices)
                    processed_chunks.append(chunk)
                except Exception as e:
                    chunk_text = chunk.get('chunk_text', '')[:30]
                    logger.error(f"Error indexing chunk '{chunk_text}...': {e}")
                    processed_chunks.append(chunk)
            
            concept['script_chunks'] = processed_chunks

        return scripts_data

    def _find_indices_for_chunk(self, chunk: Dict, block_lookup: Dict) -> Optional[Dict]:
        """
        Prepares data and calls the matcher utility to find indices for a single chunk.
        
        Args:
            chunk: A dictionary representing a single script chunk.
            block_lookup: A dictionary mapping block_ids to block objects.

        Returns:
            A dictionary with 'start_word_index' and 'end_word_index', or None if not found.
        """
        source_block_id = chunk.get('source_block_id')
        chunk_text = chunk.get('chunk_text')
        
        if not source_block_id or not chunk_text:
            return None

        source_block = block_lookup.get(source_block_id)
        if not source_block:
            logger.warning(f"Source block '{source_block_id}' not found for chunk.")
            return None

        # --- Data Preparation for Robust Matching ---

        # 1. Normalize the source block's words for a clean comparison. This
        #    involves lowercasing, removing punctuation, and filtering out non-words.
        block_words_unfiltered = source_block.get('words', [])
        normalized_block_words = [
            {'id': word['id'], 'text': normalize_word(word['text'])}
            for word in block_words_unfiltered
            if word.get('type') != 'spacing'
        ]

        # 2. Normalize the chunk's text into a comparable list of words.
        chunk_words_list = chunk_text.split()
        normalized_chunk_words = [
            {'id': i, 'text': normalize_word(word)}
            for i, word in enumerate(chunk_words_list)
        ]

        # 3. Delegate to the sequence matcher with the prepared, normalized data.
        return self.matcher.find_match(
            chunk_words=normalized_chunk_words,
            block_words=normalized_block_words
        )
