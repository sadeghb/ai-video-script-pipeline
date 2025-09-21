# src/utils/exact_sequence_matcher.py
import logging
from typing import List, Dict, Optional

class ExactSequenceMatcher:
    """
    Finds an exact sequence of words within a larger list of words.

    This utility implements a custom, efficient, boundary-based checking algorithm.
    Instead of a naive word-by-word comparison for long sequences, it optimizes the
    search by primarily checking the first and last pairs of words in the target
    sequence, making it fast and effective for its specific use case.
    """
    def __init__(self):
        """Initializes the ExactSequenceMatcher."""
        logging.info("ExactSequenceMatcher initialized.")

    def find_match(self, chunk_words: List[Dict], block_words: List[Dict]) -> Optional[Dict]:
        """
        Finds the start and end original IDs of a chunk within a block.

        Args:
            chunk_words: A list of normalized word dictionaries for the script chunk.
            block_words: A list of normalized word dictionaries for the source block.

        Returns:
            A dictionary with 'start_word_index' and 'end_word_index' (which are
            the original IDs from the transcript), or None if no match is found.
        """
        chunk_len = len(chunk_words)
        if not chunk_words or not block_words:
            return None

        # Prepare simple lists of the text content for efficient comparison.
        chunk_text_list = [w['text'] for w in chunk_words]
        block_text_list = [w['text'] for w in block_words]

        # --- Tiered Logic: Handle single-word chunks separately for efficiency ---
        if chunk_len == 1:
            try:
                match_index = block_text_list.index(chunk_text_list[0])
                matched_word_id = block_words[match_index]['id']
                return {
                    "start_word_index": matched_word_id,
                    "end_word_index": matched_word_id
                }
            except ValueError:
                return None  # Word not found in the block.

        # --- Boundary-Based Algorithm for chunks of 2 or more words ---
        elif chunk_len >= 2:
            first_pair = chunk_text_list[:2]
            last_pair = chunk_text_list[-2:]
            # The distance between the start of the first pair and the start of the last pair.
            expected_distance = chunk_len - 2

            # Iterate through all possible starting positions in the block.
            for i in range(len(block_text_list) - chunk_len + 1):
                # Step 1: Check if the first two words of the chunk match.
                if block_text_list[i : i + 2] == first_pair:
                    # If the first boundary matches, calculate where the last boundary should be.
                    last_pair_start_index = i + expected_distance
                    
                    # Step 2: Check if the last two words also match at the expected position.
                    if block_text_list[last_pair_start_index : last_pair_start_index + 2] == last_pair:
                        # Success! Both boundaries match. Assume the middle is also a match.
                        start_word_id = block_words[i]['id']
                        end_word_id = block_words[i + chunk_len - 1]['id']
                        return {
                            "start_word_index": start_word_id,
                            "end_word_index": end_word_id
                        }
        
        # If the loop completes, no match was found.
        return None
