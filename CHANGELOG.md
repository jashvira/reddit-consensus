# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2024-12-28

### Fixed
- Improved API key validation to check all required keys before prompting
- Simplified credential setup - now shows clear instructions for missing environment variables
- Removed confusing interactive credential prompts that only worked for Reddit keys

### Changed
- Streamlined API key checking logic for better user experience

## [0.1.1] - 2024-12-28

### Fixed
- Fixed console entry point `ask-reddit` command not working after pip install
- Moved CLI code into proper package module (`reddit_consensus.cli`)
- Added support for `python -m reddit_consensus` as alternative entry point

### Changed
- Reorganized CLI code from root-level script to package module for better distribution

## [0.1.0] - 2024-12-28

### Added
- Initial release of Reddit Consensus Agent
- Autonomous AI agent for analyzing Reddit discussions
- Interactive console interface with Rich UI
- Async parallel tool execution for Reddit API calls
- Two-phase research: initial research + critical analysis
- Support for OpenAI GPT models
- Command-line entry point `ask-reddit`
- Comprehensive test suite
- GitHub Actions CI/CD pipeline

### Features
- Elegant side-by-side dashboard layout
- Community-driven insights from Reddit discussions
- Balanced pros/cons analysis
- Configurable AI models
- Environment variable and interactive credential setup

[Unreleased]: https://github.com/jashvira/reddit-consensus/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/jashvira/reddit-consensus/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/jashvira/reddit-consensus/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jashvira/reddit-consensus/releases/tag/v0.1.0