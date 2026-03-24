# ---------- Dependency: Registry Core (Singleton) ----------
from functools import lru_cache

from agent_registry.config import PERSISTENCE_FILE
from agent_registry.core import RegistryCore


@lru_cache(maxsize=1)
def get_registry() -> RegistryCore:
    """
    Return a singleton instance of RegistryCore.
    The @lru_cache ensures the same instance is reused across requests,
    avoiding repeated loading of the persistence file.
    """
    return RegistryCore(persistence_file=PERSISTENCE_FILE)