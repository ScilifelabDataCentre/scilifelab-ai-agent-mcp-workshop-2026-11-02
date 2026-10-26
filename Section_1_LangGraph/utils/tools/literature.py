"""
Ready-made literature tool for the drug discovery agent in Part 2 of the LangGraph workshop.

- lit_search: research question -> PubMed passages (LitSense)
"""

from langchain.tools import tool

from utils.litsense.litsense import LitSense_API


@tool(parse_docstring=True)
def lit_search(query: str, limit: int = 20) -> str:
    """Retrieve information from PubMed using a semantic search via the LitSense API.

    Args:
        query: The research question or topic to search for in PubMed literature.
        limit: Maximum number of passages to return (default is 20).

    Returns:
        All the retrieved paragraphs with their corresponding PMID number.
    """

    try:
        engine = LitSense_API()
        results = engine.retrieve(query, limit=limit, rerank=False)
        if not results:
            return f"No relevant literature found for '{query}'. Please try a different or broader search query."
        result_str = ""
        for i, result in enumerate(results):
            result_str += (
                f"\n--- Passage #{i+1} ---\n"
                f"PMID: {result.pmid}\n"
                f"Content: {result.text}\n"
            )
        return result_str
    except Exception as e:
        return f"Error retrieving literature for '{query}': {str(e)}. Please try a different search query."
