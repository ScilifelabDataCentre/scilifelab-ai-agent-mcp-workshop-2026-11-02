# MCP Literature Review Workshop

A hands-on workshop on building and using a Model Context Protocol (MCP) server for scientific literature review.

The example uses **Europe PMC** for literature searches and **SciLifeLab OpenLLM** for model access.

## What you'll learn

Five checkpoints cover:

1. Build an MCP server with tools and resources.
2. Test the MCP client without a language model.
3. Connect an agent to the MCP server.
4. Handle errors and verify citations.
5. Enforce tool permissions and security boundaries.

## Getting started

1. Open the workshop notebook `1-mcp-hands-on/mcp_literature_review_lab.ipynb` and run cells from top to bottom.
2. Complete the sections marked `GAP`.
3. Use your own research question and query, or leave them empty for the defaults.
4. If needed, consult `1-mcp-hands-on/mcp_literature_review_solution.ipynb` for completed solutions.

The reference MCP server is provided in `server.py`. Europe PMC requires no API key.
