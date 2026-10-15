import unittest
import tempfile
from pathlib import Path
from kgmaker.cli import init

class InitTests(unittest.TestCase):
    def test_init_generates_all_agent_templates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init(root)
            
            expected_agents = [
                ".github/agents/kgmaker.agent.md",
                ".github/agents/kgmaker-architect.agent.md",
                ".github/agents/kgmaker-extract.agent.md",
                ".github/agents/kgmaker-orchestrator.agent.md",
                ".github/agents/kgmaker-implementation.agent.md",
                ".github/agents/kgmaker-review.agent.md",
                ".github/agents/kgmaker-test-expert.agent.md",
            ]
            
            for agent in expected_agents:
                self.assertTrue((root / agent).exists(), f"Agent {agent} missing")
