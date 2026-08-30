"""Small string utility module (contains two bugs for the demo)."""


def reverse_string(text: str) -> str:
    """Return the reversed version of the input string."""
    return text[::-1]


def count_vowels(text: str) -> int:
    """Return the number of vowels (a, e, i, o, u) in the text, case-insensitive."""
    vowels = "aeiou"
    return sum(1 for ch in text.lower() if ch in vowels)


def capitalize_words(text: str) -> str:
    """Capitalize the first letter of each word. (Already correct.)"""
    return " ".join(word.capitalize() for word in text.split())