# Deep Memory Search

Progressive disclosure search for Nowledge Mem knowledge base.

## Features

- **Memory Search**: Semantic search across your personal knowledge base
- **Thread Discovery**: Automatically finds related conversation threads
- **Progressive Disclosure**: Memories as summaries, threads as detailed references
- **Rich Output**: Color-coded terminal output with importance indicators

## Installation

```bash
cd /path/to/deep-mem
uv sync
```

## Configuration

Copy `.env.example` to `.env` and set your API token:

```bash
cp .env.example .env
# Edit .env with your MEM_AUTH_TOKEN
```

## Usage

```bash
# Search memories
uv run python -m deep_mem search "your query here"

# More options
uv run python -m deep_mem search "query" --limit 20 --verbose

# View full thread
uv run python -m deep_mem expand <thread_id>

# Check configuration
uv run python -m deep_mem diagnose
```

## As Claude Code Skill

This is designed to be used as a Claude Code skill. When triggered, Claude will:

1. Search memories matching your query
2. Display brief memory summaries
3. Show related threads for deeper context
4. Offer to expand specific threads on request
