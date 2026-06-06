# Contributing to Dragon

Thank you for your interest in contributing to Dragon! We welcome contributions from everyone.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues as you might find that the bug has already been reported. When creating a bug report, please include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps to reproduce the problem
- Provide specific examples to demonstrate the steps
- Describe the behavior you expected and what actually happened
- Include your OS, Python version, and Dragon version

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please:

- Use a clear and descriptive title
- Provide a detailed description of the suggested enhancement
- Explain why this enhancement would be useful
- List some examples of how this enhancement would be used

### Pull Requests

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/dragon.git
cd dragon

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy

# Install browser binaries
python -m playwright install
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_engine.py
```

## Code Style

We use Black for code formatting:

```bash
# Format code
black app/

# Check formatting
black --check app/
```

We use flake8 for linting:

```bash
# Lint code
flake8 app/
```

## Project Structure

```
dragon/
├── app/
│   ├── agents/          # Agent implementations
│   ├── core/            # Core engine and graph logic
│   ├── llm/             # LLM client and providers
│   ├── tools/           # Tool implementations
│   ├── ui/              # Terminal UI
│   └── api/             # API routes
├── config/              # Configuration files
├── tests/               # Test files
└── run.py              # Entry point
```

## Adding New Tools

1. Create a new file in `app/tools/`
2. Inherit from the `Tool` base class
3. Implement the `execute` method
4. Register the tool in the engine
5. Add tests for the tool

Example:

```python
from .registry import Tool

class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Description of my tool"
        )
    
    async def execute(self, **kwargs):
        # Your tool logic here
        return {"result": "success"}
```

## Adding New LLM Providers

1. Create a new provider class in `app/llm/client.py`
2. Inherit from `LLMProvider`
3. Implement `generate`, `generate_json`, and `chat` methods
4. Register the provider in the provider factory

## Code of Conduct

- Be respectful and inclusive
- Focus on what is best for the community
- Show empathy towards other community members

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
