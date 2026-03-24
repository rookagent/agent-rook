"""
Knowledge Loader — reads markdown knowledge files with YAML frontmatter.

Each knowledge file is a .md file with optional YAML frontmatter:

    ---
    name: module_name
    keywords:
      - keyword1
      - keyword2
    description: "What this module covers"
    ---

    # Markdown content here...

The loader extracts frontmatter metadata and content separately,
making them available for the router to build keyword mappings.
"""
import os
import logging

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 3000


def _parse_frontmatter(text: str) -> tuple:
    """
    Split a markdown file into frontmatter dict and content string.

    Returns (metadata_dict, content_string).
    If no frontmatter found, returns (empty dict, full text).
    """
    text = text.strip()

    if not text.startswith("---"):
        return {}, text

    # Find the closing --- marker
    end_idx = text.find("---", 3)
    if end_idx == -1:
        return {}, text

    frontmatter_raw = text[3:end_idx].strip()
    content = text[end_idx + 3:].strip()

    # Parse YAML frontmatter
    if yaml is not None:
        try:
            metadata = yaml.safe_load(frontmatter_raw)
            if not isinstance(metadata, dict):
                metadata = {}
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")
            metadata = {}
    else:
        # Fallback: basic key-value parsing without PyYAML
        metadata = _parse_frontmatter_basic(frontmatter_raw)

    return metadata, content


def _parse_frontmatter_basic(raw: str) -> dict:
    """
    Minimal frontmatter parser when PyYAML is not installed.
    Handles simple key: value pairs and keyword lists.
    """
    metadata = {}
    current_key = None
    current_list = None

    for line in raw.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # List item under a key
        if stripped.startswith("- ") and current_key:
            if current_list is None:
                current_list = []
            current_list.append(stripped[2:].strip().strip('"').strip("'"))
            metadata[current_key] = current_list
            continue

        # Key: value pair
        if ":" in stripped:
            if current_list is not None:
                current_list = None

            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            current_key = key

            if value:
                metadata[key] = value
            # If value is empty, might be followed by a list
            continue

    return metadata


def load_knowledge_file(filepath: str) -> dict:
    """
    Load a single markdown knowledge file.

    Returns dict with keys: name, keywords, description, content, filepath.
    Content is truncated to MAX_CONTENT_LENGTH characters.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
    except (IOError, OSError) as e:
        logger.error(f"Failed to read knowledge file {filepath}: {e}")
        return None

    metadata, content = _parse_frontmatter(raw)

    # Extract fields with sensible defaults
    filename = os.path.splitext(os.path.basename(filepath))[0]
    name = metadata.get("name", filename)
    keywords = metadata.get("keywords", [])
    description = metadata.get("description", "")

    # Ensure keywords is a list
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    # Truncate content
    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH] + "\n\n[truncated]"

    return {
        "name": name,
        "keywords": [k.lower() for k in keywords],
        "description": description,
        "content": content,
        "filepath": filepath,
    }


def load_all_knowledge(directory: str) -> list:
    """
    Scan a directory for .md files and load each one.

    Returns list of knowledge module dicts (same shape as load_knowledge_file).
    Skips files that fail to load.
    """
    modules = []

    if not os.path.isdir(directory):
        logger.warning(f"Knowledge directory not found: {directory}")
        return modules

    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(directory, filename)
        module = load_knowledge_file(filepath)
        if module:
            modules.append(module)
            logger.debug(
                f"Loaded knowledge module: {module['name']} "
                f"({len(module['keywords'])} keywords)"
            )

    logger.info(f"Loaded {len(modules)} knowledge modules from {directory}")
    return modules
