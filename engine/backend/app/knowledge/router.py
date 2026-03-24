"""
Knowledge Router — routes free-text queries to the correct knowledge module.

At startup, scans the agent/knowledge/ directory for markdown files with
YAML frontmatter. Builds a keyword-to-module mapping automatically —
no hardcoded routes needed.

Usage:
    from knowledge.router import KnowledgeRouter

    router = KnowledgeRouter("/path/to/agent/knowledge")
    result = router.route_knowledge_query("how do I sauté onions?")
    if result:
        module_name, description, content = result
"""
import logging
from .loader import load_all_knowledge

logger = logging.getLogger(__name__)


class KnowledgeRouter:
    """
    File-driven knowledge router.

    Scans a directory of markdown files at init time, builds keyword
    mappings from YAML frontmatter, and routes queries by matching
    query words against keywords.
    """

    def __init__(self, knowledge_dir: str = None):
        """
        Initialize the router by loading all knowledge files.

        Args:
            knowledge_dir: Path to directory containing .md knowledge files.
                           If None, router starts empty (call load() later).
        """
        self._modules = []
        self._routes = []  # List of (keywords, module_name, description, content)

        if knowledge_dir:
            self.load(knowledge_dir)

    def load(self, knowledge_dir: str):
        """
        Load (or reload) knowledge modules from a directory.

        Clears any previously loaded modules before scanning.
        """
        self._modules = load_all_knowledge(knowledge_dir)
        self._routes = []

        for module in self._modules:
            self._routes.append((
                module["keywords"],
                module["name"],
                module["description"],
                module["content"],
            ))

        logger.info(
            f"Knowledge router initialized: {len(self._routes)} modules, "
            f"{sum(len(r[0]) for r in self._routes)} total keywords"
        )

    def route_knowledge_query(self, query: str):
        """
        Route a free-text query to the best-matching knowledge module.

        Keyword matching is case-insensitive. Checks if any keyword
        appears as a substring in the query. First match wins — modules
        are checked in file-load order (alphabetical by filename).

        Returns:
            (module_name, description, content) tuple on match.
            None if no keywords match.
        """
        if not query:
            return None

        q_lower = query.lower().strip()

        for keywords, module_name, description, content in self._routes:
            for keyword in keywords:
                if keyword in q_lower:
                    logger.debug(
                        f"Knowledge router: '{query[:60]}' -> "
                        f"{module_name} (matched '{keyword}')"
                    )
                    return (module_name, description, content)

        logger.debug(f"Knowledge router: '{query[:60]}' -> no match")
        return None

    def get_all_modules(self) -> list:
        """
        Return list of all loaded modules as (name, description) tuples.
        """
        return [(m["name"], m["description"]) for m in self._modules]

    def get_module_by_name(self, name: str):
        """
        Look up a specific module by name.

        Returns (name, description, content) or None.
        """
        for module in self._modules:
            if module["name"] == name:
                return (module["name"], module["description"], module["content"])
        return None

    @property
    def module_count(self) -> int:
        return len(self._modules)
