import unittest
from dataclasses import dataclass
from typing import Optional

from webapp.models import PaginatedResult
from webapp.service import RecipeService


@dataclass
class _StubSearchRepository:
    result: Optional[PaginatedResult] = None
    error: Optional[Exception] = None

    def search(
        self,
        query,
        ingredients,
        page,
        page_size,
        cuisines=None,
        meals=None,
        diets=None,
    ):
        if self.error is not None:
            raise self.error
        return self.result


@dataclass
class _StubDetailRepository:
    result: PaginatedResult
    search_calls: int = 0

    def search(
        self,
        query,
        ingredients,
        page,
        page_size,
        cuisines=None,
        meals=None,
        diets=None,
    ):
        self.search_calls += 1
        return self.result


class RecipeServiceTests(unittest.TestCase):
    def test_falls_back_to_sql_when_enabled(self) -> None:
        search_repository = _StubSearchRepository(error=RuntimeError("ES unavailable"))
        fallback_result = PaginatedResult(
            items=[],
            total=0,
            page=1,
            page_size=20,
            backend="sql",
        )
        detail_repository = _StubDetailRepository(result=fallback_result)
        service = RecipeService(
            search_repository,
            detail_repository,
            page_size=20,
            allow_sql_fallback=True,
        )

        result = service.search("pasta", 1)

        self.assertEqual(result.backend, "sql")
        self.assertEqual(detail_repository.search_calls, 1)

    def test_raises_when_fallback_disabled(self) -> None:
        search_repository = _StubSearchRepository(error=RuntimeError("ES unavailable"))
        detail_repository = _StubDetailRepository(
            result=PaginatedResult(items=[], total=0, page=1, page_size=20, backend="sql")
        )
        service = RecipeService(
            search_repository,
            detail_repository,
            page_size=20,
            allow_sql_fallback=False,
        )

        with self.assertRaisesRegex(RuntimeError, "ES unavailable"):
            service.search("pasta", 1)

        self.assertEqual(detail_repository.search_calls, 0)


if __name__ == "__main__":
    unittest.main()
