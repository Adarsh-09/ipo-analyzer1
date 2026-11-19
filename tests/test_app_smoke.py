import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
PAGES = [APP / "Home.py", *sorted((APP / "pages").glob("*.py"))]


class TestAppSmoke(unittest.TestCase):
    def test_every_page_runs_without_exception(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                at = AppTest.from_file(str(page), default_timeout=180).run()
                self.assertFalse(at.exception, [str(e.value) for e in at.exception])


if __name__ == "__main__":
    unittest.main()