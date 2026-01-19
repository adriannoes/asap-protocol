"""ULID-based ID generation for ASAP protocol entities.

ULIDs (Universally Unique Lexicographically Sortable Identifiers) provide:
- 128-bit compatibility with UUID
- Lexicographic sorting by timestamp
- Canonically encoded as 26-character string (Crockford's Base32)
- Monotonically increasing within the same millisecond
"""

from datetime import datetime

from ulid import ULID


def generate_id() -> str:
    """Generate a new ULID string.
    
    Returns:
        A 26-character ULID string that is:
        - Globally unique
        - Lexicographically sortable by creation time
        - URL-safe (uses Crockford's Base32 alphabet)
    
    Example:
        >>> id1 = generate_id()
        >>> len(id1)
        26
        >>> id2 = generate_id()
        >>> id1 < id2  # Sortable by time
        True
    """
    return str(ULID())


def extract_timestamp(ulid: str) -> datetime:
    """Extract the timestamp from a ULID string.
    
    Args:
        ulid: A 26-character ULID string
        
    Returns:
        A timezone-aware datetime in UTC representing when the ULID was created
        
    Raises:
        ValueError: If the ULID string is invalid
        
    Example:
        >>> ulid = generate_id()
        >>> timestamp = extract_timestamp(ulid)
        >>> timestamp.tzinfo == timezone.utc
        True
    """
    ulid_obj = ULID.from_str(ulid)
    # ULID.datetime returns a timezone-aware datetime in UTC
    return ulid_obj.datetime
