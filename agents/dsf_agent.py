"""
DSF Agent: Deep Sci-Fi World Building Agent

This agent uses the Letta platform with evaluation tools to create
scientifically-grounded fictional worlds.
"""

import os
from typing import Optional

from dotenv import load_dotenv

from .prompts import DSF_SYSTEM_PROMPT

# Load environment variables
load_dotenv()


class DSFAgent:
    """Deep Sci-Fi World Building Agent using Letta platform."""

    def __init__(
        self,
        base_url: str = "http://localhost:8283",
        api_key: Optional[str] = None,
    ):
        """
        Initialize DSF Agent.

        Args:
            base_url: Letta server URL (default: local server)
            api_key: Letta API key (optional for local server)
        """
        try:
            from letta import LettaClient
        except ImportError:
            raise ImportError(
                "letta-client not installed. Run: pip install letta-client"
            )

        self.base_url = base_url
        self.api_key = api_key or os.getenv("LETTA_API_KEY")
        self.client = None
        self.agent_id = None

    def connect(self):
        """Connect to Letta server."""
        from letta import LettaClient

        if self.api_key:
            self.client = LettaClient(
                base_url=self.base_url,
                token=self.api_key,
            )
        else:
            # Local server without auth
            self.client = LettaClient(base_url=self.base_url)

        print(f"✓ Connected to Letta server at {self.base_url}")

    def create_agent(
        self,
        name: str = "dsf-agent",
        model: str = "claude-sonnet-4-5-20250929",
    ):
        """
        Create a new DSF agent with evaluation tools.

        Args:
            name: Agent name
            model: LLM model to use

        Returns:
            Agent object
        """
        if not self.client:
            self.connect()

        # Get or create user
        try:
            user = self.client.user
        except Exception:
            user = None

        # Create agent with DSF system prompt and evaluation tools
        agent = self.client.create_agent(
            name=name,
            llm_config={
                "model": model,
                "model_endpoint_type": "anthropic",
            },
            # Tools will be automatically available from Letta platform
            # including: send_message, memory, conversation_search,
            # assess_output_quality, check_logical_consistency,
            # compare_versions, analyze_information_gain
            memory={
                "human": "User wants to create deep, scientifically-grounded sci-fi worlds",
                "persona": DSF_SYSTEM_PROMPT,
            },
        )

        self.agent_id = agent.id
        print(f"✓ Created agent '{name}' (ID: {agent.id})")
        print(f"  Model: {model}")
        print(f"  Evaluation tools: assess_output_quality, check_logical_consistency, compare_versions, analyze_information_gain")

        return agent

    def send_message(self, message: str):
        """
        Send a message to the agent.

        Args:
            message: User message

        Returns:
            Agent response
        """
        if not self.agent_id:
            raise ValueError("No agent created. Call create_agent() first.")

        response = self.client.send_message(
            agent_id=self.agent_id,
            message=message,
            role="user",
        )

        return response

    def get_agent(self, agent_id: Optional[str] = None):
        """
        Get agent details.

        Args:
            agent_id: Agent ID (uses current agent if not specified)

        Returns:
            Agent object
        """
        if not self.client:
            self.connect()

        agent_id = agent_id or self.agent_id
        if not agent_id:
            raise ValueError("No agent ID specified")

        return self.client.get_agent(agent_id)

    def list_agents(self):
        """List all agents."""
        if not self.client:
            self.connect()

        return self.client.list_agents()


def main():
    """Example usage of DSF Agent."""
    # Initialize agent
    dsf = DSFAgent(base_url="http://localhost:8283")

    # Connect to Letta server
    dsf.connect()

    # Create agent
    agent = dsf.create_agent(name="dsf-worldbuilder")

    # Example interaction
    print("\n=== Example: Create a world ===")
    response = dsf.send_message(
        "I want to create a hard sci-fi world about a generation ship "
        "traveling to another star. The focus should be on how the closed "
        "ecosystem affects society over generations."
    )

    print("\n=== Agent Response ===")
    for message in response.messages:
        if message.role == "assistant":
            print(message.text)


if __name__ == "__main__":
    main()
