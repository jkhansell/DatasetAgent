from langchain.messages import SystemMessage, HumanMessage
from agent import download_agent
from utils.logging import log_section
from utils.config import load_config
from utils.types import DatasetState

config = load_config()

def download_node(state: DatasetState):
    log_section("NODE: DOWNLOAD")
    state["phase"] = "download"

    sources = state["sources"].copy()
    
    for iid, entry in sources.items():
        if entry.download_status == "classified" and entry.downloader_type and entry.downloader_id:
            target_dir = f"./data/downloads/{iid}/"
            
            print(f"Attempting agentic download for: {entry.title}")
            print(f"Type: {entry.downloader_type}, Identifier: {entry.downloader_id}, URL: {entry.url}")
            
            prompt = config["prompts"]["download"]
            human_msg = f"""
            Identify the best way to download this dataset and WRITE CODE (Python or Bash) to perform the download.
            
            Dataset Title: {entry.title}
            URL: {entry.url}
            Type: {entry.downloader_type}
            Identifier: {entry.downloader_id}
            
            Requirements:
            1. Create the target directory: {target_dir}
            2. Write a script (e.g., download_{iid}.py or .sh) that handles the download.
            3. Execute the script.
            4. Handle any necessary post-processing (unzip, untar, etc.).
            5. Ensure the final data is in {target_dir}.
            
            Use your available tools:
            - `scrape_website`: To find direct download links or documentation if needed.
            - `run_shell`: To create files, run commands (wget, curl, git, kaggle, etc.), and execute your scripts.
            
            Return a message confirming success and the final local path.
            """
            
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=human_msg)
            ]
            
            result = download_agent.invoke({"messages": messages})
            
            response_text = result["messages"][-1].content
            print(f"Agent response: {response_text}")
            
            # Simple heuristic for success, can be improved
            if any(marker in response_text.lower() for marker in ["success", "downloaded", "local path", target_dir]):
                entry.download_status = "success"
                entry.local_path = target_dir
                print(f"✅ Downloaded {entry.title} to {target_dir}")
            else:
                entry.download_status = "failed"
                print(f"❌ Failed to download {entry.title}")

    return {"sources": sources}

    return {"sources": sources}
