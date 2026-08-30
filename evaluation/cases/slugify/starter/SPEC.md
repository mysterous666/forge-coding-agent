# `slugify(text, max_length=50)`

- Normalize accented Latin characters to their ASCII base characters.
- Lowercase the result.
- Replace every run of non-ASCII-alphanumeric characters with one hyphen.
- Remove leading and trailing hyphens.
- Truncate to `max_length`, then remove a trailing hyphen if truncation created one.
- Raise `ValueError` when `max_length < 1`.
