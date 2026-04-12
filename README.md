# DatasetAgent

DatasetAgent is a generic agentic workflow designed for automated data discovery, website scraping, and structured metadata storage. While initially motivated by biomedical dataset research, the architecture is entirely general-purpose and can be configured for any domain via its YAML-based prompting system.

## Features

- **Automated Discovery**: Uses search engines and website scraping to identify relevant data sources.
- **YAML-Driven Prompts**: Easily adapt the agent's behavior and domain expertise without modifying code.
- **Stateful URL Tracking**: Programmatically maintains a persistent "seen" list to avoid redundant processing.
- **Integrated vLLM Support**: Built-in readiness checks ensure your local LLM server is healthy before execution.
- **Structured Storage**: Automatically populates a local SQLite database with extracted metadata.

## Installation

This project uses `uv` for lightning-fast dependency management.

1. **Environment Setup**:
   Copy the environment template and fill in your API keys (e.g., TAVILY_API_KEY):
   ```bash
   cp env_template .env
   ```

2. **Install Core Dependencies**:
   ```bash
   uv sync
   ```

2. **Install vLLM**:
   VLLM is used for high-performance local inference. Install it separately to ensure the latest CUDA/hardware-specific optimizations:
   ```bash
   uv pip install vllm --torch-backend=auto
   ```

3. **Download LLM Models**:
   Install the Hugging Face CLI to download models:
   ```bash
   uv pip install huggingface_hub
   # Example
   hf download Qwen/Qwen2.5-Coder-7B-Instruct
   ```

## Getting Started

### 1. Configure the Agent
Edit `configs/dataset_agent.yaml` to define your target domain, prompts, and model settings:

```yaml
target_sources: 10
prompts:
  discovery: "Your custom role and rules for the agent..."
```

### 2. Start the LLM Server
Use the provided script to serve your model (e.g., Qwen 3.5) via vLLM:

```bash
bash scripts/vllm_serve.sh start
```

### 3. Run the Discovery Workflow
Execute the main script. The agent will automatically wait for the vLLM server to be ready:

```bash
python main.py --target 20
```

## Potential Applications

- **Academic Literature Review**: Discovering and indexing relevant papers or supplementary datasets.
- **Market Research**: Scraping and structuring product information or competitor data.
- **OSINT**: Collecting and organizing open-source intelligence on specific topics.
- **Dataset Curation**: Automating the first stage of data collection for machine learning projects.

## Project Structure

- `state_agent/`: Core logic, state graph, and utility functions.
- `configs/`: YAML configuration for prompts and goals.
- `scripts/`: Infrastructure scripts for vLLM and housekeeping.
- `data/`: Local storage for the SQLite database and generated summaries.
