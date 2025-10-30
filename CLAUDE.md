# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a PR Review Agent built using **Google ADK** (Agent Development Kit). The project uses Google's Gemini models via Vertex AI for agent-based interactions.

Documentation for Google ADK is https://google.github.io/adk-docs/

## Environment Setup

The project uses a Python virtual environment located at `venv/`.

**Activate the environment:**
```bash
source venv/bin/activate
```

**Required environment variables (in `pr_agent/.env`):**
- `GOOGLE_GENAI_USE_VERTEXAI=1` - Enables Vertex AI integration
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `GOOGLE_CLOUD_LOCATION` - GCP region (e.g., `europe-west2`)

## Architecture

### Core Components

**`pr_agent/agent.py`** - Defines the root agent using Google ADK:
- Uses `google.adk.agents.llm_agent.Agent` class
- Configured with `gemini-2.5-flash` model
- Agent name: `root_agent`
- Currently set up as a general-purpose assistant

**`pr_agent/__init__.py`** - Package initialization that imports the agent module

### Technology Stack

- **Google ADK (v1.17.0)** - Agent Development Kit for building LLM agents
- **Google GenAI (v1.47.0)** - Gemini model integration
- **Google Cloud AI Platform (v1.123.0)** - Vertex AI backend
- **Google Cloud services** - Various GCP integrations (BigQuery, Storage, Logging, etc.)

## Development Workflow

Since this project is not yet a git repository and has minimal structure, standard development commands are:

**Run Python scripts:**
```bash
source venv/bin/activate
python -m pr_agent.agent  # or other entry points as developed
```

**Install new dependencies:**
```bash
pip install <package-name>
pip freeze > requirements.txt  # if you create this file
```

## Key Considerations

1. **Authentication**: The project uses Vertex AI, so ensure you're authenticated with GCP:
   ```bash
   gcloud auth application-default login
   ```

2. **Agent Configuration**: The root agent in `pr_agent/agent.py` can be customized by modifying:
   - `model`: Change the Gemini model version
   - `name`: Agent identifier
   - `description`: Agent purpose description
   - `instruction`: System prompt/instructions for the agent

3. **Google ADK Patterns**: When extending this agent:
   - Agents are instantiated from `google.adk.agents.llm_agent.Agent`
   - Agents can be composed hierarchically for complex workflows
   - Tools and capabilities can be added to agents through ADK's tool framework
