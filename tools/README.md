# Tools

This directory contains tool implementations for agents.

## Structure

### data/
Data retrieval and grounding tools:
- `azure_search.py` - Azure AI Search integration for document retrieval
- `bing_search.py` - Bing Search API for web grounding
- `grounding.py` - Combined grounding logic

### actions/
Action-based tools:
- `booking_mcp.py` - MCP server integration for booking operations
- `mcp_client.py` - Generic MCP client utilities

## Purpose

Tools provide the functional capabilities that agents can invoke to accomplish tasks, separated into data retrieval (grounding) and actionable operations.
