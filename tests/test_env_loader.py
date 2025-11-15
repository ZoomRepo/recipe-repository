from pathlib import Path
import unittest
from unittest import mock

from webapp.scripts import env_loader


class LoadDotenvTests(unittest.TestCase):
    def test_uses_project_dotenv_when_available(self) -> None:
        fake_dotenv = mock.Mock()
        with mock.patch.dict("sys.modules", {"dotenv": fake_dotenv}):
            env_loader.load_dotenv_if_available()

        project_root = Path(env_loader.__file__).resolve().parents[2]
        fake_dotenv.load_dotenv.assert_called_once_with(
            dotenv_path=project_root / ".env", override=False
        )

    def test_uses_explicit_path(self) -> None:
        fake_dotenv = mock.Mock()
        with mock.patch.dict("sys.modules", {"dotenv": fake_dotenv}):
            env_loader.load_dotenv_if_available(Path("/tmp/test.env"), override=True)

        fake_dotenv.load_dotenv.assert_called_once_with(
            dotenv_path=Path("/tmp/test.env"), override=True
        )

    def test_returns_false_when_library_missing(self) -> None:
        with mock.patch.dict("sys.modules", {"dotenv": None}):
            result = env_loader.load_dotenv_if_available()

        self.assertFalse(result)
