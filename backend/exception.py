from dataclasses import dataclass

@dataclass
class LoadError(Exception):
    """Raise an exception where data loading fails"""

    source: str
    message: str
    original_error: Exception | None = None

    def __str__(self):
        return f"Failed to load from {self.source}: {self.message}"
