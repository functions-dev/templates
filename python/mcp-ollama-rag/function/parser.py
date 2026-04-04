import requests
from urllib.parse import urlparse

_tokenizer = None

# The tokenizer is downloaded from HuggingFace Hub on first use and cached
# locally. If you hit rate limits, log in with: huggingface-cli login
# To bundle it locally instead, run:
#   python -c "from tokenizers import Tokenizer; Tokenizer.from_pretrained('mixedbread-ai/mxbai-embed-large-v1').save('function/tokenizer.json')"
# then use: _tokenizer = Tokenizer.from_file("function/tokenizer.json")
_TOKENIZER_MODEL = "mixedbread-ai/mxbai-embed-large-v1"


def _get_tokenizer():
    """Lazily load the tokenizer for the default embedding model."""
    global _tokenizer
    if _tokenizer is None:
        from tokenizers import Tokenizer
        _tokenizer = Tokenizer.from_pretrained(_TOKENIZER_MODEL)
    return _tokenizer


def is_url(text: str) -> bool:
    """Check if text is a valid URL."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_raw_content(url: str) -> str:
    """Retrieve contents of a URL as text."""
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def chunk_text(text: str, max_tokens: int = 480, overlap_tokens: int = 30) -> list[str]:
    """Split text into chunks that fit within the embedding model's context
    window, using the model's actual tokenizer for precise token counting.

    Args:
        text: The text to chunk.
        max_tokens: Max tokens per chunk. Default 480 leaves headroom
                    within the 512-token context of mxbai-embed-large.
        overlap_tokens: Number of overlapping tokens between chunks.
    """
    tokenizer = _get_tokenizer()
    token_ids = tokenizer.encode(text).ids

    if len(token_ids) <= max_tokens:
        return [text]

    # Sliding window: advance by (max_tokens - overlap) to keep overlap between chunks
    chunks = []
    start = 0
    step = max_tokens - overlap_tokens
    while start < len(token_ids):
        end = min(start + max_tokens, len(token_ids))
        chunk = tokenizer.decode(token_ids[start:end])
        chunks.append(chunk)
        start += step

    return chunks


def resolve_input(item: str) -> str:
    """Resolve a single input item: fetch URL content or return raw text."""
    if is_url(item):
        return get_raw_content(item)
    return item
