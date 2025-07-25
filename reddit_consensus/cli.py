#!/usr/bin/env python3

"""
Reddit Consensus Agent - Interactive CLI
Ask Reddit for insights and get balanced perspectives from community discussions.
"""

import asyncio
import getpass
import os

from rich.panel import Panel
from rich.prompt import Prompt

from .colors import console, print_colored, print_phase_header
from .recommender import AutonomousRedditConsensus


def check_api_keys():
    """Check if API keys are available"""
    print_phase_header("Reddit Consensus Agent", "Checking API configuration...")

    missing_keys = []

    # Check OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print_colored("SUCCESS", "OpenAI API key found")
    else:
        print_colored("ERROR", "OpenAI API key missing")
        missing_keys.append("OPENAI_API_KEY")

    # Check Reddit keys
    reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_user_agent = os.getenv("REDDIT_USER_AGENT")

    if reddit_client_id and reddit_client_secret and reddit_user_agent:
        print_colored("SUCCESS", "Reddit API credentials found")
    else:
        print_colored("ERROR", "Reddit API credentials missing")
        if not reddit_client_id:
            missing_keys.append("REDDIT_CLIENT_ID")
        if not reddit_client_secret:
            missing_keys.append("REDDIT_CLIENT_SECRET")
        if not reddit_user_agent:
            missing_keys.append("REDDIT_USER_AGENT")

    # If any keys missing, show instructions
    if missing_keys:
        print()
        print("Please set the following environment variables:")
        for key in missing_keys:
            if key == "OPENAI_API_KEY":
                print(f"export {key}='your-openai-api-key'  # Get from https://platform.openai.com/api-keys")
            elif key == "REDDIT_CLIENT_ID":
                print(f"export {key}='your-reddit-client-id'  # Get from https://www.reddit.com/prefs/apps/")
            elif key == "REDDIT_CLIENT_SECRET":
                print(f"export {key}='your-reddit-client-secret'")
            elif key == "REDDIT_USER_AGENT":
                print(f"export {key}='YourApp/1.0 (by /u/yourusername)'")
        print()
        print("Then restart the application.")
        return False

    return True


def setup_reddit_keys():
    """Interactively collect Reddit API credentials"""
    print()
    print("Enter Reddit API credentials (get from https://www.reddit.com/prefs/apps/):")

    client_id = Prompt.ask("[bold]Reddit Client ID[/bold]").strip()
    if not client_id:
        print_colored("ERROR", "Client ID required")
        return False

    client_secret = getpass.getpass("Reddit Client Secret: ").strip()
    if not client_secret:
        print_colored("ERROR", "Client Secret required")
        return False

    user_agent = Prompt.ask(
        "[bold]Reddit User Agent[/bold]", default="RedditConsensus/1.0"
    ).strip()
    if not user_agent:
        user_agent = "RedditConsensus/1.0"

    # Set for current session
    os.environ["REDDIT_CLIENT_ID"] = client_id
    os.environ["REDDIT_CLIENT_SECRET"] = client_secret
    os.environ["REDDIT_USER_AGENT"] = user_agent

    print_colored("SUCCESS", "Reddit credentials set for this session")
    return True


async def ask_query():
    """Get user query and process it"""
    console.print()

    # Create input prompt panel
    prompt_panel = Panel.fit(
        "[bold blue]What would you like to ask the Reddit hive mind?[/bold blue]\n"
        + "[dim]Examples: 'best coffee shops in tokyo', 'budget laptops under $800', 'reliable used cars'[/dim]",
        style="blue",
        padding=(1, 2),
    )
    console.print(prompt_panel)

    query = Prompt.ask("\n[bold cyan]Your query[/bold cyan]", console=console).strip()

    if not query:
        print("Please enter a query to get insights.")
        return False

    print()

    try:
        # Create and run agent
        agent = AutonomousRedditConsensus()
        result = await agent.process_query(query)

        # Show results
        agent.print_results()

        # Show summary
        print()
        console.print(
            f"[bold]✓ Found {len(result['recommendations'])} insights | "
            f"{result['steps']} reasoning steps[/bold]"
        )

        return True

    except Exception as e:
        print_colored("ERROR", f"Failed to process query: {str(e)}")
        return False


def ask_continue():
    """Ask if user wants to continue"""
    print()
    while True:
        response = Prompt.ask(
            "\n[bold green]Ask another query?[/bold green]",
            choices=["y", "n"],
            default="y",
        ).lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


async def interactive_main():
    """Main interactive session"""
    # Check API keys
    if not check_api_keys():
        return

    print()
    print_colored("SUCCESS", "Ready to analyze Reddit discussions!")

    # Main query loop
    while True:
        success = await ask_query()

        if success and ask_continue():
            continue
        else:
            break

    print()
    print_colored("SUCCESS", "Thanks for using Reddit Consensus Agent!")


def main():
    """Synchronous entry point for console script"""
    try:
        asyncio.run(interactive_main())
    except KeyboardInterrupt:
        print()
        print_colored("SUCCESS", "Goodbye!")
    except Exception as e:
        print_colored("ERROR", f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()