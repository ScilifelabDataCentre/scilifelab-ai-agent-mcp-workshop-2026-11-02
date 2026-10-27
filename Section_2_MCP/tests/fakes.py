"""Synthetic Europe PMC payloads for tests. These are invented records, not real papers."""

SEARCH_PAYLOAD = {
    "version": "test",
    "hitCount": 2,
    "resultList": {
        "result": [
            {
                "id": "11111111", "source": "MED", "pmid": "11111111", "pmcid": "PMC2222222",
                "doi": "10.1234/synthetic.a", "title": "Synthetic record A: <i>subgroups</i> &amp; outcomes",
                "authorString": "Doe J, Roe R, Poe P.", "journalTitle": "Journal of Tests",
                "pubYear": "2021", "citedByCount": 42, "isOpenAccess": "Y",
                "abstractText": "<h4>Background</h4>Synthetic abstract A. " + "word " * 300,
            },
            {
                "id": "PPR000001", "source": "PPR", "doi": "10.1234/synthetic.b",
                "title": "Synthetic preprint B", "authorString": "Smith A.",
                "journalInfo": {"journal": {"title": "Preprint Server"}, "yearOfPublication": 2024},
                "citedByCount": "3", "isOpenAccess": "N",
            },
        ]
    },
}

PAPER_PAYLOAD = {
    "hitCount": 1,
    "resultList": {"result": [dict(
        SEARCH_PAYLOAD["resultList"]["result"][0],
        keywordList={"keyword": ["clustering", "outcomes"]},
        meshHeadingList={"meshHeading": [{"descriptorName": "Diabetes Mellitus, Type 2"}]},
        pubTypeList={"pubType": "research-article"},
        fullTextUrlList={"fullTextUrl": [{"url": "https://example.org/fulltext/a"}]},
        firstPublicationDate="2021-03-01",
    )]},
}

CITATIONS_PAYLOAD = {
    "hitCount": 1,
    "citationList": {"citation": [
        {"id": "33333333", "source": "MED", "title": "Synthetic citing record C",
         "authorString": "Lee K.", "journalAbbreviation": "J Test", "pubYear": 2025, "citedByCount": 0},
    ]},
}
