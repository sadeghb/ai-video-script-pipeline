# src/services/id_mapping_service.py
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class IdMappingService:
    """
    Processes client-side transcript data into standardized internal formats.

    This service is a crucial pre-processing step that decouples the core pipeline
    from the client's specific data format. It ingests a transcript that may
    use arbitrary string-based IDs and creates two clean, internally-consistent
    versions for different processing needs, along with a map to translate back
    to the original IDs.
    """

    def __init__(self):
        """Initializes the ID mapping service."""
        logger.info("IdMappingService initialized.")

    def run(self, transcript_data: Dict) -> Tuple[Dict, Dict, Dict]:
        """
        Maps arbitrary client IDs to sequential integer IDs for robust processing.

        This method executes a three-step process:
        1.  Normalizes spacing by inserting standardized space objects.
        2.  Assigns a new, sequential integer ID to every object (words, pauses,
            spaces) and builds a map to link back to the original client IDs.
        3.  Creates two distinct transcript versions:
            - full_objects_transcript: Contains all items with new integer IDs.
            - textual_transcript: A filtered version optimized for text analysis,
              with pauses removed and spacing durations adjusted.

        Args:
            transcript_data: The original transcript data object from the client,
                             expected to have a 'words' key with a list of items.

        Returns:
            A tuple containing:
            - textual_transcript (Dict): A transcript version for text processing.
            - full_objects_transcript (Dict): A complete, indexed transcript.
            - id_map (Dict): A mapping from new integer IDs to original client IDs.
        """
        id_map = {}
        full_objects_list = []
        original_items = transcript_data.get('words', [])

        # Step 1: Normalize the transcript by inserting standardized space objects
        # between every original item to ensure consistent structure.
        temp_list_with_spacing = []
        for item in original_items:
            temp_list_with_spacing.append(item)
            space_obj = {
                "text": " ",
                "start": item.get('end'),
                "end": item.get('end'),
                "type": "spacing",
                "speaker_id": item.get('speaker_id')
            }
            temp_list_with_spacing.append(space_obj)

        # Step 2: Assign a sequential integer ID to every object and build the
        # mapping from the new ID back to the original client ID.
        for i, item_obj in enumerate(temp_list_with_spacing):
            new_item = item_obj.copy()
            original_id = new_item.get('id')
            new_id = i

            new_item['id'] = new_id
            if original_id is not None:
                id_map[new_id] = original_id

            full_objects_list.append(new_item)

        # Step 3: Create a second, "textual" transcript version by filtering
        # out non-essential types (like pauses) and refining spacing durations.
        textual_objects_list_pre = [
            item for item in full_objects_list if item.get('type') != 'pause'
        ]

        # Adjust spacing timestamps to fill the gaps left by removed pauses.
        final_textual_list = []
        for i, item in enumerate(textual_objects_list_pre):
            if item.get('type') == 'spacing' and i < len(textual_objects_list_pre) - 1:
                next_item = textual_objects_list_pre[i+1]
                item['end'] = next_item.get('start')

            final_textual_list.append(item)

        # Assemble the final transcript objects for output.
        full_objects_transcript = {**transcript_data, 'words': full_objects_list}
        textual_transcript = {**transcript_data, 'words': final_textual_list}

        logger.info("Successfully processed and mapped transcript IDs.")
        return textual_transcript, full_objects_transcript, id_map
