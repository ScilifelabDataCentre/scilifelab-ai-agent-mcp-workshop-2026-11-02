"""Unit tests for the Europe PMC client. Standard library only, no network: python -m unittest"""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from litreview import config, europepmc
from tests.section_2_mcp.fakes import CITATIONS_PAYLOAD, PAPER_PAYLOAD, SEARCH_PAYLOAD


class CacheTestCase(unittest.TestCase):
    """Each test gets an empty cache directory and offline mode."""

    def setUp(self):
        self._saved = (config.CACHE_DIR, config.MODE, config.EUROPEPMC_BASE_URL)
        self._tmp = tempfile.TemporaryDirectory()
        config.CACHE_DIR = Path(self._tmp.name)
        config.MODE = "offline"
        config.EUROPEPMC_BASE_URL = "https://example.invalid/rest"

    def tearDown(self):
        config.CACHE_DIR, config.MODE, config.EUROPEPMC_BASE_URL = self._saved
        self._tmp.cleanup()

    def store(self, url, payload):
        path = europepmc.cache_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"url": url, "retrieved_at": "2026-10-26T00:00:00+00:00", "payload": payload}))


class InputTests(unittest.TestCase):
    def test_empty_query_uses_default(self):
        self.assertEqual(europepmc.validate_query("   "), config.DEFAULT_QUERY)
        self.assertEqual(europepmc.validate_query(None), config.DEFAULT_QUERY)

    def test_long_query_is_refused(self):
        with self.assertRaises(europepmc.InvalidInput):
            europepmc.validate_query("x" * (config.MAX_QUERY_CHARS + 1))

    def test_results_are_clamped(self):
        self.assertEqual(europepmc.clamp_results(10_000), config.MAX_RESULTS_LIMIT)
        for bad in (0, -1, "many", None):
            with self.assertRaises(europepmc.InvalidInput):
                europepmc.clamp_results(bad)

    def test_years(self):
        self.assertEqual(europepmc.validate_years(2015, None), (2015, None))
        with self.assertRaises(europepmc.InvalidInput):
            europepmc.validate_years(2020, 2010)
        with self.assertRaises(europepmc.InvalidInput):
            europepmc.validate_years(1500, None)

    def test_identifiers(self):
        cases = {
            "12345678": ("MED", "12345678"),
            "PMID: 12345678": ("MED", "12345678"),
            "pmc1234567": ("PMC", "PMC1234567"),
            "ppr123": ("PPR", "PPR123"),
            "10.1038/s41586-020-2649-2": ("DOI", "10.1038/s41586-020-2649-2"),
            "https://doi.org/10.1038/abc": ("DOI", "10.1038/abc"),
            "MED:42": ("MED", "42"),
        }
        for raw, expected in cases.items():
            self.assertEqual(europepmc.normalize_id(raw), expected, raw)
        for bad in ("", "not-an-id", "10.1/x", "MED:12; DROP"):
            with self.assertRaises(europepmc.InvalidInput, msg=bad):
                europepmc.normalize_id(bad)


class QueryTests(unittest.TestCase):
    def test_filters_and_sort_go_into_the_query(self):
        query = europepmc.build_query('"a b" OR c', from_year=2020, to_year=2024,
                                      open_access_only=True, sort="cited")
        self.assertEqual(
            query, '("a b" OR c) AND FIRST_PDATE:[2020-01-01 TO 2024-12-31] AND OPEN_ACCESS:y sort_cited:y'
        )

    def test_unknown_sort_is_refused(self):
        with self.assertRaises(europepmc.InvalidInput):
            europepmc.build_query("x", sort="alphabetical")

    def test_url_is_encoded(self):
        url = europepmc.search_url('"a b" AND c', 5)
        self.assertIn("query=%22a+b%22+AND+c", url)
        self.assertIn("resultType=core", url)
        self.assertIn("pageSize=5", url)


class ParsingTests(unittest.TestCase):
    def test_core_record(self):
        paper = europepmc.parse_paper(SEARCH_PAYLOAD["resultList"]["result"][0], 100)
        self.assertEqual(paper["id"], "MED:11111111")
        self.assertEqual(paper["title"], "Synthetic record A: subgroups & outcomes")
        self.assertTrue(paper["open_access"])
        self.assertEqual(paper["cited_by"], 42)
        self.assertLessEqual(len(paper["abstract"]), 100)
        self.assertNotIn("<h4>", paper["abstract"])
        self.assertEqual(paper["url"], "https://europepmc.org/article/MED/11111111")

    def test_record_with_journal_info(self):
        paper = europepmc.parse_paper(SEARCH_PAYLOAD["resultList"]["result"][1], None)
        self.assertEqual(paper["journal"], "Preprint Server")
        self.assertEqual(paper["year"], 2024)
        self.assertEqual(paper["cited_by"], 3)
        self.assertFalse(paper["open_access"])
        self.assertIsNone(paper["abstract"])


class OfflineCacheTests(CacheTestCase):
    def test_search_from_cache(self):
        full = europepmc.build_query(config.DEFAULT_QUERY)
        self.store(europepmc.search_url(full, 5), SEARCH_PAYLOAD)
        result = europepmc.search("", max_results=5)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["served_from"], "cache")
        self.assertEqual(result["hit_count"], 2)
        self.assertEqual([p["id"] for p in result["papers"]], ["MED:11111111", "PPR:PPR000001"])

    def test_no_results_is_a_status_not_an_error(self):
        full = europepmc.build_query("nothing here")
        self.store(europepmc.search_url(full, 3), {"hitCount": 0, "resultList": {"result": []}})
        result = europepmc.search("nothing here", max_results=3)
        self.assertEqual(result["status"], "no_results")
        self.assertEqual(result["papers"], [])

    def test_offline_miss_is_explicit(self):
        with self.assertRaises(europepmc.NotInCache) as caught:
            europepmc.search("a query that was never cached", max_results=3)
        self.assertEqual(caught.exception.kind, "offline_cache_miss")

    def test_clamp_warning(self):
        full = europepmc.build_query(config.DEFAULT_QUERY)
        self.store(europepmc.search_url(full, config.MAX_RESULTS_LIMIT), SEARCH_PAYLOAD)
        result = europepmc.search("", max_results=500)
        self.assertTrue(result["warnings"])

    def test_get_paper(self):
        self.store(europepmc.search_url("EXT_ID:11111111 AND SRC:MED", 1), PAPER_PAYLOAD)
        result = europepmc.get_paper("PMID:11111111")
        self.assertEqual(result["status"], "ok")
        paper = result["paper"]
        self.assertEqual(paper["mesh_terms"], ["Diabetes Mellitus, Type 2"])
        self.assertEqual(paper["publication_types"], ["research-article"])
        self.assertEqual(paper["full_text_links"], ["https://example.org/fulltext/a"])

    def test_get_paper_not_found(self):
        self.store(europepmc.search_url("PMCID:PMC9999999", 1), {"hitCount": 0, "resultList": {"result": []}})
        self.assertEqual(europepmc.get_paper("PMC9999999")["status"], "not_found")

    def test_citing_papers(self):
        self.store(europepmc.citations_url("MED", "11111111", 10), CITATIONS_PAYLOAD)
        result = europepmc.citing_papers("MED:11111111")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["papers"][0]["pmid"], "33333333")
        self.assertIsNone(result["papers"][0]["open_access"])

    def test_strip_abstracts(self):
        full = europepmc.build_query(config.DEFAULT_QUERY)
        self.store(europepmc.search_url(full, 5), SEARCH_PAYLOAD)
        self.assertEqual(europepmc.strip_abstracts_in_cache(), 1)
        self.assertIsNone(europepmc.search("", max_results=5)["papers"][0]["abstract"])


class LiveModeTests(CacheTestCase):
    def setUp(self):
        super().setUp()
        config.MODE = "live"

    def test_network_failure_is_an_upstream_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")), \
             mock.patch("time.sleep"):
            with self.assertRaises(europepmc.UpstreamError) as caught:
                europepmc.search("x", max_results=1)
        self.assertEqual(caught.exception.kind, "upstream_error")

    def test_client_error_is_not_retried(self):
        error = urllib.error.HTTPError("u", 400, "bad", {}, io.BytesIO(b""))
        with mock.patch("urllib.request.urlopen", side_effect=error) as opened:
            with self.assertRaises(europepmc.UpstreamError):
                europepmc.search("x", max_results=1)
        self.assertEqual(opened.call_count, 1)

    def test_non_json_is_an_upstream_error(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"<html>maintenance</html>"
        with mock.patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(europepmc.UpstreamError):
                europepmc.search("x", max_results=1)

    def test_live_answer_is_cached(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(SEARCH_PAYLOAD).encode()
        with mock.patch("urllib.request.urlopen", return_value=response):
            first = europepmc.search("cache me", max_results=2)
        self.assertEqual(first["served_from"], "live")
        config.MODE = "offline"
        self.assertEqual(europepmc.search("cache me", max_results=2)["served_from"], "cache")


if __name__ == "__main__":
    unittest.main()
