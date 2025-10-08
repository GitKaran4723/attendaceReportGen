# Contributing to Attendance Analyzer

Thank you for considering contributing to Attendance Analyzer! 🎉

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Sample Excel file (if possible)
- Screenshots (if applicable)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:
- Clear description of the feature
- Use cases and examples
- Any potential implementation ideas

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages**: `git commit -m "Add feature: description"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Open a Pull Request**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/attendaceReportGen.git
cd attendaceReportGen

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## Code Style

- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Add docstrings to functions
- Comment complex logic
- Keep functions focused and modular

## Testing

Before submitting:
- Test with various Excel file formats
- Verify edge cases (missing data, empty columns, etc.)
- Check PDF report generation
- Ensure no crashes on malformed data

## Documentation

- Update README.md if adding features
- Add entries to CHANGELOG.md
- Update relevant .md files in the docs folder
- Include code comments for complex logic

## Questions?

Feel free to open an issue with the "question" label!

Thank you for contributing! 🙌
