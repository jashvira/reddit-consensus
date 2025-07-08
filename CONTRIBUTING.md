# Contributing to Reddit Consensus Agent

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/jashvira/reddit-consensus.git
   cd reddit-consensus
   ```

2. **Install with development dependencies**
   ```bash
   uv sync --group dev
   ```

3. **Set up pre-commit hooks** (optional but recommended)
   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=reddit_consensus

# Run specific test file
uv run pytest tests/test_tools.py -v
```

## Code Style

We use `black` and `ruff` for code formatting and linting:

```bash
# Format code
uv run black .

# Check linting
uv run ruff check .

# Type checking
uv run mypy reddit_consensus/
```

## Releasing New Versions

1. **Update version in `pyproject.toml`**
2. **Update `CHANGELOG.md`** with new changes
3. **Create a GitHub release** with version tag (e.g., `v0.1.1`)
4. **GitHub Actions will automatically publish to PyPI**

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code is formatted
6. Update documentation if needed
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to your branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request