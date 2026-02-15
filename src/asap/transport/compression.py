"""Compression support for ASAP protocol transport layer.

This module provides compression and decompression utilities for reducing
bandwidth usage in agent-to-agent communication.

Supported compression algorithms:
- gzip: Standard compression, widely supported (default)
- brotli: Better compression ratio (optional, requires brotli package)

Compression is applied automatically when:
- Request body exceeds COMPRESSION_THRESHOLD (default: 1KB)
- Server indicates support via Accept-Encoding header

Example:
    >>> from asap.transport.compression import compress_payload, decompress_payload
    >>>
    >>> # Compress large payload
    >>> data = b'{"large": "payload..."}' * 100
    >>> compressed, encoding = compress_payload(data)
    >>> # encoding = "gzip" or "br" depending on configuration
    >>>
    >>> # Decompress received payload
    >>> original = decompress_payload(compressed, encoding)
"""

import gzip
from enum import Enum

from asap.observability import get_logger

# Module logger
logger = get_logger(__name__)

# Compression threshold: only compress payloads larger than this size (bytes)
COMPRESSION_THRESHOLD = 1024  # 1KB

# Gzip compression level (1-9, higher = better compression but slower)
GZIP_COMPRESSION_LEVEL = 6


class CompressionAlgorithm(str, Enum):
    """Supported compression algorithms."""

    GZIP = "gzip"
    BROTLI = "br"
    IDENTITY = "identity"  # No compression


def is_brotli_available() -> bool:
    try:
        import brotli  # noqa: F401

        return True
    except ImportError:
        return False


def get_supported_encodings() -> list[str]:
    encodings = ["gzip"]
    if is_brotli_available():
        encodings.insert(0, "br")  # Prefer brotli when available
    return encodings


def get_accept_encoding_header() -> str:
    encodings = get_supported_encodings()
    # Add identity as fallback (always supported)
    encodings.append("identity")
    return ", ".join(encodings)


def compress_gzip(data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=GZIP_COMPRESSION_LEVEL)


def decompress_gzip(data: bytes) -> bytes:
    return gzip.decompress(data)


def compress_brotli(data: bytes) -> bytes:
    import brotli

    # Quality 4 is a good balance of speed and compression ratio
    result: bytes = brotli.compress(data, quality=4)
    return result


def decompress_brotli(data: bytes) -> bytes:
    import brotli

    try:
        result: bytes = brotli.decompress(data)
        return result
    except brotli.error as e:
        raise OSError(f"Brotli decompression failed: {e}") from e


def compress_payload(
    data: bytes,
    preferred_algorithm: CompressionAlgorithm | None = None,
    threshold: int = COMPRESSION_THRESHOLD,
) -> tuple[bytes, CompressionAlgorithm]:
    """Compress payload if it exceeds threshold.

    Compresses the payload using the preferred algorithm if specified,
    otherwise uses the best available algorithm (brotli > gzip).

    Args:
        data: Raw bytes to compress
        preferred_algorithm: Optional preferred compression algorithm.
            If None, uses brotli if available, otherwise gzip.
        threshold: Minimum payload size to trigger compression (default: 1KB).
            Payloads smaller than this are returned as-is with IDENTITY encoding.

    Returns:
        Tuple of (compressed_data, algorithm_used)
        If compression is skipped, returns (original_data, IDENTITY)

        >>> compressed, algorithm = compress_payload(data)
        >>> print(f"Compressed {len(data)} -> {len(compressed)} bytes using {algorithm.value}")

    Note:
        Compression adds CPU overhead which may increase latency for very small payloads.
        For extremely latency-sensitive scenarios, consider increasing the threshold
        or disabling compression if payloads are typically small.
    """
    # Skip compression for small payloads
    if len(data) < threshold:
        logger.debug(
            "asap.compression.skipped",
            size=len(data),
            threshold=threshold,
            reason="payload_below_threshold",
        )
        return data, CompressionAlgorithm.IDENTITY

    # Determine algorithm to use
    if preferred_algorithm is not None:
        algorithm = preferred_algorithm
    elif is_brotli_available():
        # TODO: Add prefer_fast_compression option to prefer gzip even when brotli is available
        algorithm = CompressionAlgorithm.BROTLI
    else:
        algorithm = CompressionAlgorithm.GZIP

    # Skip if identity is requested
    if algorithm == CompressionAlgorithm.IDENTITY:
        return data, CompressionAlgorithm.IDENTITY

    # Compress using selected algorithm
    original_size = len(data)
    try:
        if algorithm == CompressionAlgorithm.BROTLI:
            compressed = compress_brotli(data)
        else:
            compressed = compress_gzip(data)

        compressed_size = len(compressed)
        reduction_pct = (1 - compressed_size / original_size) * 100

        logger.debug(
            "asap.compression.applied",
            algorithm=algorithm.value,
            original_size=original_size,
            compressed_size=compressed_size,
            reduction_percent=round(reduction_pct, 1),
        )

        # Only use compression if it actually reduces size
        if compressed_size >= original_size:
            logger.debug(
                "asap.compression.ineffective",
                algorithm=algorithm.value,
                original_size=original_size,
                compressed_size=compressed_size,
                reason="compression_increased_size",
            )
            return data, CompressionAlgorithm.IDENTITY

        return compressed, algorithm

    except ImportError:
        # Brotli not available, fallback to gzip
        logger.warning(
            "asap.compression.fallback",
            requested=algorithm.value,
            fallback="gzip",
            reason="brotli_not_installed",
        )
        return compress_payload(data, CompressionAlgorithm.GZIP, threshold)
    except Exception as e:
        # Compression failed, return original
        logger.warning(
            "asap.compression.failed",
            algorithm=algorithm.value,
            error=str(e),
            error_type=type(e).__name__,
        )
        return data, CompressionAlgorithm.IDENTITY


def decompress_payload(
    data: bytes,
    encoding: str,
) -> bytes:
    """Decompress payload based on Content-Encoding header.

    Args:
        data: Compressed bytes
        encoding: Content-Encoding header value (e.g., "gzip", "br", "identity")

    Returns:
        Decompressed bytes

    Raises:
        ValueError: If encoding is not supported
        OSError: If decompression fails (invalid compressed data)

    Example:
        >>> compressed_data = gzip.compress(b'{"message": "hello"}')
        >>> original = decompress_payload(compressed_data, "gzip")
    """
    # Normalize encoding name
    encoding_lower = encoding.lower().strip()

    # Handle identity (no compression)
    if encoding_lower in ("identity", ""):
        return data

    original_size = len(data)

    try:
        if encoding_lower == "gzip":
            decompressed = decompress_gzip(data)
        elif encoding_lower == "br":
            if not is_brotli_available():
                raise ValueError(
                    "Brotli decompression requested but brotli package is not installed. "
                    "Install with: pip install brotli"
                )
            decompressed = decompress_brotli(data)
        else:
            raise ValueError(
                f"Unsupported Content-Encoding: {encoding}. Supported: gzip, br, identity"
            )

        decompressed_size = len(decompressed)
        logger.debug(
            "asap.decompression.applied",
            encoding=encoding_lower,
            compressed_size=original_size,
            decompressed_size=decompressed_size,
        )

        return decompressed

    except ImportError as e:
        raise ValueError(
            f"Cannot decompress {encoding}: required package not installed. {e}"
        ) from e


def select_best_encoding(accept_encoding: str | None) -> CompressionAlgorithm:
    """Select best compression algorithm based on Accept-Encoding header.

    Parses the Accept-Encoding header and selects the best supported algorithm
    based on client preferences and availability.

    Args:
        accept_encoding: Accept-Encoding header value (e.g., "gzip, br;q=0.9")
            If None, returns IDENTITY (no compression).

    Returns:
        Best available compression algorithm

    Example:
        >>> algorithm = select_best_encoding("br, gzip;q=0.9, identity;q=0.5")
        >>> print(algorithm.value)  # "br" if brotli available, else "gzip"
    """
    if not accept_encoding:
        return CompressionAlgorithm.IDENTITY

    # Parse Accept-Encoding header (simplified parser)
    # Format: encoding[;q=weight], encoding[;q=weight], ...
    encodings: dict[str, float] = {}
    for part in accept_encoding.split(","):
        part = part.strip()
        if not part:
            continue

        # Split encoding and quality
        if ";q=" in part.lower():
            encoding, q_str = part.lower().split(";q=", 1)
            try:
                quality = float(q_str)
            except ValueError:
                quality = 1.0
        else:
            encoding = part.lower()
            quality = 1.0

        encoding = encoding.strip()
        if encoding:
            encodings[encoding] = quality

    # Sort by quality (highest first) and filter to supported encodings
    supported = get_supported_encodings()
    candidates: list[tuple[str, float]] = []

    for enc, quality in encodings.items():
        if enc in supported or enc == "identity":
            candidates.append((enc, quality))

    # Sort by quality descending
    candidates.sort(key=lambda x: x[1], reverse=True)

    if not candidates:
        return CompressionAlgorithm.IDENTITY

    best_encoding = candidates[0][0]

    if best_encoding == "br" and is_brotli_available():
        return CompressionAlgorithm.BROTLI
    if best_encoding == "gzip":
        return CompressionAlgorithm.GZIP
    return CompressionAlgorithm.IDENTITY
