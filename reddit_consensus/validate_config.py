#!/usr/bin/env python3
"""
Configuration validation script for Reddit Consensus system.
Run this to check if all required configuration is properly set up.
"""

from .config import validate_config, get_reddit_credentials, REDDIT_ENV_VARS
import sys
import os


def main():
    """Validate all configuration and provide helpful feedback."""
    print("Validating Reddit Consensus Configuration...")

    # Check environment variables
    missing_vars = []
    for key, env_var in REDDIT_ENV_VARS.items():
        value = os.getenv(env_var)
        if not value:
            missing_vars.append(env_var)

    if missing_vars:
        print(f"Missing environment variables: {', '.join(missing_vars)}")
        print("Set them with:")
        for var in missing_vars:
            print(f"  export {var}='your_value'")
        return False

    # Try to get credentials
    try:
        credentials = get_reddit_credentials()
        print("Configuration valid - all credentials found")
        return True
    except ValueError as e:
        print(f"Configuration error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)