# src/services/chunker_service.py
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ChunkerService:
    """
    Transforms a word-level transcript into a list of semantic blocks.

    Blocks are continuous segments of speech from a single speaker, constrained
    by a maximum word count. This service is a pre-processing step to create
    appropriately sized, contextually relevant chunks of text for analysis
    by downstream LLM services.
    """

    def __init__(self, config: Dict):
        """
        Initializes the service with configuration for block creation.

        Args:
            config: A dictionary containing chunker settings, primarily:
                    'block_max_words' (int): The hard limit for words in a block.
                    'soft_limit_ratio' (float): A ratio to determine the soft
                                                word limit for breaking on punctuation.
        """
        logger.info("ChunkerService initialized.")
        self.block_max_words = int(config.get('block_max_words', 300))
        soft_limit_ratio = float(config.get('soft_limit_ratio', 0.8))
        self.soft_word_limit = int(self.block_max_words * soft_limit_ratio)

        if self.block_max_words <= 0:
            raise ValueError("block_max_words must be a positive integer.")

    def run(self, transcript_data: Dict) -> List[Dict]:
        """
        Groups words from a transcript into blocks based on speaker and word count.

        Args:
            transcript_data: A transcript object containing a "words" list.

        Returns:
            A list of block dictionaries, each representing a semantic chunk.
        """
        words = transcript_data.get("words", [])
        if not words:
            logger.warning("No words found in transcript data; returning empty list.")
            return []

        blocks = self._chunk_words_into_blocks(words)
        logger.info(f"Successfully created {len(blocks)} blocks from transcript.")
        return blocks

    def _chunk_words_into_blocks(self, words: List[Dict]) -> List[Dict]:
        """Iterates through words and groups them into coherent blocks."""
        blocks = []
        block_counter = 0
        current_word_index = 0

        while current_word_index < len(words):
            end_index = self._find_block_end(words, current_word_index)
            block_words = words[current_word_index : end_index + 1]

            block_obj = self._create_block_object(block_words, block_counter)
            if block_obj:
                blocks.append(block_obj)
                block_counter += 1

            current_word_index = end_index + 1
        return blocks

    def _find_block_end(self, words: List[Dict], start_index: int) -> int:
        """
        Determines the end index for a block based on a set of rules.

        A block ends when one of the following conditions is met first:
        1. The speaker changes.
        2. The word count exceeds the 'soft limit' AND a sentence-ending
           punctuation mark is found.
        3. The word count reaches the 'hard limit' (`block_max_words`).
        """
        word_count = 0
        initial_speaker = None

        # Find the first 'word' type to determine the block's primary speaker.
        for i in range(start_index, len(words)):
            if words[i].get('type') == 'word':
                initial_speaker = words[i].get('speaker_id')
                break
        
        # If no speaker is found (e.g., only pauses left), end the block.
        if initial_speaker is None:
            return len(words) - 1

        for i in range(start_index, len(words)):
            word_data = words[i]
            if word_data.get('type') != 'word':
                continue

            # Condition 1: Speaker change
            if word_data.get('speaker_id') != initial_speaker:
                return i - 1

            word_count += 1
            
            # Condition 2: Soft limit break on sentence-ending punctuation
            ends_with_punctuation = word_data['text'].strip().endswith(('.', '?', '!'))
            if word_count > self.soft_word_limit and ends_with_punctuation:
                return self._include_trailing_space_if_present(i, words)
            
            # Condition 3: Hard word count limit
            if word_count >= self.block_max_words:
                return self._include_trailing_space_if_present(i, words)

        return len(words) - 1

    @staticmethod
    def _include_trailing_space_if_present(index: int, words: List[Dict]) -> int:
        """Extends the block to include a single trailing space object, if it exists."""
        if index + 1 < len(words) and words[index + 1].get('type') == 'spacing':
            return index + 1
        return index

    @staticmethod
    def _create_block_object(word_list: List[Dict], block_id: int) -> Optional[Dict]:
        """Creates a single block dictionary from a list of word objects."""
        actual_words = [w for w in word_list if w.get('type') == 'word']
        if not actual_words:
            return None

        full_text = "".join([w['text'] for w in word_list]).strip()
        if not full_text:
            return None

        return {
            "block_id": f"block_{block_id:03d}",
            "speaker": actual_words[0].get('speaker_id', 'unknown'),
            "start_time": word_list[0]['start'],
            "end_time": word_list[-1]['end'],
            "text": full_text,
            "words": word_list
        }
