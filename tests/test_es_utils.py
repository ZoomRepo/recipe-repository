import unittest
from unittest import mock

from elasticsearch.exceptions import BadRequestError, NotFoundError
from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig

from webapp.scripts import es_utils


def _make_meta(status: int) -> ApiResponseMeta:
    return ApiResponseMeta(
        status=status,
        http_version="1.1",
        headers=HttpHeaders(),
        duration=0.0,
        node=NodeConfig(scheme="http", host="localhost", port=9200),
    )


def _bad_request(status: int = 400) -> BadRequestError:
    return BadRequestError(message="bad", meta=_make_meta(status), body=None)


def _not_found() -> NotFoundError:
    return NotFoundError(message="missing", meta=_make_meta(404), body=None)


class IndexExistsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = mock.Mock()

    def test_returns_boolean_from_exists_call(self) -> None:
        self.client.indices.exists.return_value = True
        self.assertTrue(es_utils.index_exists(self.client, "recipes"))
        self.client.indices.exists.assert_called_once_with(index="recipes")

    def test_head_bad_request_falls_back_to_get(self) -> None:
        self.client.indices.exists.side_effect = _bad_request()
        self.client.indices.get.return_value = {"recipes": {}}

        self.assertTrue(es_utils.index_exists(self.client, "recipes"))
        self.client.indices.get.assert_called_once_with(index="recipes")

    def test_fallback_handles_missing_index(self) -> None:
        self.client.indices.exists.side_effect = _bad_request()
        self.client.indices.get.side_effect = _not_found()

        self.assertFalse(es_utils.index_exists(self.client, "recipes"))

    def test_fallback_reraises_on_invalid_index(self) -> None:
        self.client.indices.exists.side_effect = _bad_request()
        self.client.indices.get.side_effect = _bad_request()

        with self.assertRaises(BadRequestError):
            es_utils.index_exists(self.client, "recipes")

    def test_non_retryable_bad_request_is_propagated(self) -> None:
        self.client.indices.exists.side_effect = _bad_request(status=401)

        with self.assertRaises(BadRequestError):
            es_utils.index_exists(self.client, "recipes")
