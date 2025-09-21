# src/utils/text_utils.py
import re
import string

def normalize_word(text: str) -> str:
    """Converts text to lowercase and removes all punctuation."""
    text = text.lower()
    # This removes all punctuation characters
    return text.translate(str.maketrans('', '', string.punctuation))
