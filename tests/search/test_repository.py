import unittest
from unittest.mock import MagicMock

from webapp.search.repository import ElasticsearchSearchRepository


class ElasticsearchSearchRepositoryTests(unittest.TestCase):
    def test_search_uses_valid_sort_payload(self) -> None:
        client = MagicMock()
        client.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": [],
            }
        }
        repository = ElasticsearchSearchRepository(client, "recipes")

        repository.search("chicken nuggets", None, page=1, page_size=20)

        kwargs = client.search.call_args.kwargs
        self.assertEqual(
            kwargs["sort"],
            [
                {"_score": "desc"},
                {"updated_at": "desc"},
                {"id": "desc"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
