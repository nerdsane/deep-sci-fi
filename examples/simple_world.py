"""
Simple example of using DSF Agent to create a world.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.dsf_agent import DSFAgent


def main():
    """Create a simple world with DSF Agent."""
    print("=== DSF Agent: Simple World Creation Example ===\n")

    # Initialize agent (connects to local Letta server)
    dsf = DSFAgent(base_url="http://localhost:8283")

    # Connect to server
    print("Connecting to local Letta server...")
    dsf.connect()

    # Create agent with DSF system prompt and evaluation tools
    print("\nCreating DSF agent...")
    agent = dsf.create_agent(
        name="dsf-worldbuilder",
        model="claude-sonnet-4-5-20250929",
    )

    # Create a world
    print("\n=== Creating a generation ship world ===\n")
    response = dsf.send_message(
        "I want to create a hard sci-fi world about a generation ship "
        "traveling to Proxima Centauri. The ship left Earth 80 years ago "
        "and has 40 years left. Focus on: (1) How the closed ecosystem works, "
        "(2) How society has evolved after 3 generations in space, "
        "(3) What conflicts arise from limited resources. "
        "\n\n"
        "Please create 2-3 world options that explore different approaches, "
        "then I'll pick one to develop further."
    )

    # Print response
    print("\n=== Agent Response ===\n")
    for message in response.messages:
        if message.role == "assistant":
            print(message.text)
            print()

    # Example: Evaluate world quality
    print("\n=== Example: Agent can self-evaluate ===")
    print("The agent has access to evaluation tools and can use them to:")
    print("- assess_output_quality() - check world against quality rubrics")
    print("- check_logical_consistency() - find contradictions")
    print("- compare_versions() - measure improvement between iterations")
    print("- analyze_information_gain() - assess novelty of changes")
    print("\nThe agent will use these proactively based on the system prompt.")


if __name__ == "__main__":
    main()
