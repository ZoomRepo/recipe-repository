import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from webapp.config import AppConfig, ElasticsearchConfig
from webapp.search.indexer import RecipeDocumentBuilder, RecipeSearchIndexer


class RecipeDocumentBuilderTests(unittest.TestCase):
    def test_builds_document_from_db_row(self) -> None:
        row = {
            "id": 5,
            "source_name": "Example",
            "source_url": "https://example.com/recipe",
            "title": "Test Recipe",
            "description": "Tasty",
            "ingredients": "[\"flour\", \"sugar\"]",
            "instructions": ["Mix", "Bake"],
            "prep_time": "10 mins",
            "cook_time": "20 mins",
            "total_time": "30 mins",
            "servings": "4",
            "image": "http://example.com/image.jpg",
            "author": "Chef",
            "categories": ["Dessert"],
            "tags": "[\"sweet\"]",
            "raw": {"nutrition": {"calories": 200}},
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime(2024, 1, 2, 12, 0, 0),
        }

        document = RecipeDocumentBuilder.from_row(row)

        self.assertEqual(document["id"], 5)
        self.assertIn({"raw": "flour", "name": "flour"}, document["ingredients"])
        self.assertEqual(document["instructions"], "Mix\n\nBake")
        self.assertEqual(document["nutrients"], {"calories": 200})
        self.assertIn("suggest", document)
        self.assertIn("Test Recipe", document["suggest"]["input"])
        self.assertIn("flour", document["suggest"]["input"])
        self.assertEqual(document["created_at"], "2024-01-01T12:00:00")
        self.assertEqual(document["updated_at"], "2024-01-02T12:00:00")


class RecipeSearchIndexerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.indexer = RecipeSearchIndexer(self.client, "recipes-index")

    def test_from_config_sets_compatibility_headers(self) -> None:
        es_config = ElasticsearchConfig(
            url="http://localhost:9200",
            compatibility_version=8,
        )
        config = AppConfig(elasticsearch=es_config)

        with patch("webapp.search.indexer.Elasticsearch") as es:
            es.return_value = MagicMock()
            RecipeSearchIndexer.from_config(config)

        self.assertTrue(es.called)
        kwargs = es.call_args.kwargs
        self.assertIn("headers", kwargs)
        self.assertFalse(kwargs.get("api_versioning", True))
        self.assertEqual(
            kwargs["headers"],
            {
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8",
            },
        )

    def test_upsert_row_indexes_document(self) -> None:
        row = {
            "id": 1,
            "source_name": "Example",
            "source_url": "https://example.com",
            "title": "Indexed",
            "ingredients": ["egg"],
            "instructions": ["Boil"],
        }

        self.indexer.upsert_row(row)

        self.client.index.assert_called_once()
        kwargs = self.client.index.call_args.kwargs
        self.assertEqual(kwargs["index"], "recipes-index")
        self.assertEqual(kwargs["id"], 1)
        self.assertEqual(kwargs["document"]["title"], "Indexed")

    def test_bulk_index_invokes_helpers(self) -> None:
        documents = [
            {"id": 1, "title": "One"},
            {"id": 2, "title": "Two"},
        ]
        with patch("webapp.search.indexer.helpers.bulk") as bulk:
            self.indexer.bulk_index(documents)

        bulk.assert_called_once()
        actions = list(bulk.call_args[0][1])
        self.assertEqual(actions[0]["_id"], 1)
        self.assertEqual(actions[1]["_source"], {"id": 2, "title": "Two"})

    def test_invalid_compatibility_version_defaults_to_8(self) -> None:
        es_config = ElasticsearchConfig(
            url="http://localhost:9200",
            compatibility_version=9,
        )
        config = AppConfig(elasticsearch=es_config)

        with patch("webapp.search.indexer.Elasticsearch") as es, self.assertLogs(
            "webapp.search.indexer", level="WARNING"
        ) as log:
            es.return_value = MagicMock()
            RecipeSearchIndexer.from_config(config)

        kwargs = es.call_args.kwargs
        self.assertFalse(kwargs.get("api_versioning", True))
        self.assertEqual(
            kwargs["headers"],
            {
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8",
            },
        )
        self.assertTrue(
            any("defaulting to 8" in message for message in log.output),
            log.output,
        )


if __name__ == "__main__":
    unittest.main()
