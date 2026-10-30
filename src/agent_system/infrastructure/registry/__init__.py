"""Target-local Agent Registry backed by the Target Database."""
from uuid import UUID
from agent_system.contracts.models import Agent
from agent_system.domain.errors import DomainError

class RegistryError(DomainError):
    code = "AGENT_REGISTRY_INVALID"

class AgentRegistry:
    KEY = "registry:agents:v1"
    def __init__(self, store): self.store = store
    def register(self, agent: Agent) -> Agent:
        if agent.kind != "internal" or agent.runtime != "python-worker":
            raise RegistryError("MVP registry accepts registered internal Python workers only")
        if agent.provider not in {"text.echo", "math.sum"}:
            raise RegistryError("worker is not in the built-in allowlist")
        records = self.store.get_config(self.KEY) if self._exists() else []
        if any(row["agent_id"] == str(agent.agent_id) or row["name"].casefold() == agent.name.casefold() for row in records):
            raise RegistryError("Agent ID or name already registered")
        records.append(agent.model_dump(mode="json"))
        self.store.set_config(self.KEY, records)
        return agent
    def _exists(self):
        try: self.store.get_config(self.KEY); return True
        except KeyError: return False
    def list(self):
        return [Agent.model_validate(row) for row in (self.store.get_config(self.KEY) if self._exists() else [])]
    def select(self, capability: str) -> Agent:
        matches = [a for a in self.list() if a.status == "active" and a.availability == "available" and capability in a.capabilities]
        if not matches: raise RegistryError(f"no available Agent for capability {capability}")
        return matches[0]
