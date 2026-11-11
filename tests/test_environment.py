"""
Environment and Project Setup Test Suite
Validates directory structure, configuration parsing, data dictionary presence, and environment integrity.
Uses unittest (standard library) for zero-dependency execution, fully compatible with pytest.
"""

import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestEnvironmentSetup(unittest.TestCase):
    """Test suite validating Phase 0 deliverables and project structure."""

    def test_python_version(self):
        """Verify that Python version is 3.11+ (Python 3.11 or 3.12 recommended)."""
        self.assertGreaterEqual(
            sys.version_info[:2],
            (3, 11),
            f"Python 3.11+ is required. Found: {sys.version}",
        )

    def test_project_directory_structure(self):
        """Verify all mandatory project directories exist."""
        required_directories = [
            "config",
            "data/raw",
            "data/interim",
            "data/processed",
            "notebooks",
            "src/collection",
            "src/cleaning",
            "src/features",
            "src/fundamental_analysis",
            "src/models",
            "src/evaluation",
            "src/rag",
            "app/pages",
            "app/components",
            "models",
            "reports/figures",
            "reports/evaluation",
            "tests",
            "docs",
        ]

        for rel_path in required_directories:
            dir_path = PROJECT_ROOT / rel_path
            self.assertTrue(
                dir_path.exists(), f"Missing required directory: {rel_path}"
            )
            self.assertTrue(
                dir_path.is_dir(), f"Path is not a directory: {rel_path}"
            )

    def test_package_init_files_exist(self):
        """Verify __init__.py files exist across all modular src packages."""
        packages = [
            "src",
            "src/collection",
            "src/cleaning",
            "src/features",
            "src/fundamental_analysis",
            "src/models",
            "src/evaluation",
            "src/rag",
            "app",
            "tests",
        ]

        for pkg in packages:
            init_file = PROJECT_ROOT / pkg / "__init__.py"
            self.assertTrue(
                init_file.exists(), f"Missing __init__.py in package: {pkg}"
            )

    def test_config_example_file(self):
        """Verify that settings.example.yaml exists and contains required sections."""
        config_file = PROJECT_ROOT / "config" / "settings.example.yaml"
        self.assertTrue(config_file.exists(), "Missing config/settings.example.yaml")

        content = config_file.read_text(encoding="utf-8")
        required_sections = [
            "project:",
            "paths:",
            "scraping:",
            "datasets:",
            "ml_pipeline:",
            "pre_close:",
            "post_close:",
            "rag_engine:",
            "dashboard:",
        ]
        for section in required_sections:
            self.assertIn(
                section,
                content,
                f"Missing section '{section}' in settings.example.yaml",
            )

    def test_data_dictionary_exists_and_contains_schemas(self):
        """Verify data dictionary template exists and defines all 3 required tables."""
        dict_path = PROJECT_ROOT / "docs" / "data_dictionary.md"
        self.assertTrue(dict_path.exists(), "docs/data_dictionary.md must exist")

        content = dict_path.read_text(encoding="utf-8")
        self.assertIn("ipo_features.csv", content)
        self.assertIn("ipo_outcomes.csv", content)
        self.assertIn("ipo_gmp_history.csv", content)
        self.assertIn("ipo_id", content)
        self.assertIn("pre_close", content)
        self.assertIn("post_close", content)
        self.assertIn("listing_open_price", content)

    def test_gitignore_security_rules(self):
        """Verify .gitignore prevents accidental check-in of secrets, venvs, and binaries."""
        gitignore_path = PROJECT_ROOT / ".gitignore"
        self.assertTrue(gitignore_path.exists(), ".gitignore must exist")

        content = gitignore_path.read_text(encoding="utf-8")
        critical_patterns = [".env", "venv", "__pycache__", "chroma_db", "*.joblib", "data/raw/*"]
        for pattern in critical_patterns:
            self.assertIn(
                pattern,
                content,
                f"Missing critical pattern in .gitignore: {pattern}",
            )

    def test_env_example_exists(self):
        """Verify .env.example exists with required API key placeholders."""
        env_example = PROJECT_ROOT / ".env.example"
        self.assertTrue(env_example.exists(), ".env.example must exist")

        content = env_example.read_text(encoding="utf-8")
        self.assertIn("GEMINI_API_KEY", content)
        self.assertIn("ENVIRONMENT", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
