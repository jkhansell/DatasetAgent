from agent import discovery_agent
from utils.db import db_string
from utils.logging import log_section
from utils.parsing import load_jl
from utils.config import load_config
from langchain.messages import HumanMessage, SystemMessage
from utils.types import DatasetState
import os, subprocess

config = load_config()

def rescrape_node(state: DatasetState):
    log_section("NODE: RESCRAPE")
    state["phase"] = "rescrape"
    
    sources = state["sources"].copy()
    updated = False
    
    threshold = config.get("confidence_threshold", 0.7)
    max_rescrape = config.get("max_rescrape", 2)
    
    for iid, entry in sources.items():
        if entry.download_status == "low_confidence" and entry.rescrape_count < max_rescrape:
            print(f"🔍 Rescraping {entry.url} (Attempt {entry.rescrape_count + 1})")
            
            # Use scrape_website tool via subprocess or agent
            output_file = f"temp_rescrape_{iid}.jl"
            cmd = f"scrapy runspider ./scripts/spider.py -a start_url={entry.url} -o {output_file}"
            subprocess.run(cmd, shell=True, capture_output=True)
            
            if os.path.exists(output_file):
                data = load_jl(output_file)
                os.remove(output_file)
                
                if not data:
                    print(f"⚠️ Failed to get text for {entry.url}")
                    entry.rescrape_count += 1
                    continue
                    
                full_text = data[0].get("text", "")
                links = data[0].get("links", [])
                
                # Use discovery_agent to synthesize new metadata from raw text
                messages = [
                    SystemMessage(content=config["prompts"]["rescrape"]),
                    HumanMessage(content=config["prompts"]["rescrape_human"].format(
                        url=entry.url,
                        scraped_text=f"TEXT:\n{full_text}\n\nLINKS:\n{links}",
                        db_string=db_string
                    ))
                ]
                
                result = discovery_agent.invoke({"messages": messages})
                
                if "structured_response" in result and result["structured_response"].entries:
                    # Merge information - take the first synthesized entry
                    synthesized_entry = list(result["structured_response"].entries.values())[0]
                    
                    # Extension check for synthesized entry
                    excluded_extensions = config.get("excluded_extensions", [])
                    if any(synthesized_entry.url.lower().endswith(ext.lower()) for ext in excluded_extensions):
                        print(f"🚫 Synthesis returned forbidden extension ({synthesized_entry.url}). Marking as failed.")
                        entry.download_status = "failed"
                        entry.rescrape_count += 1
                        continue

                    # Update fields while preserving IID and URL
                    entry.title = synthesized_entry.title or entry.title
                    entry.description = synthesized_entry.description or entry.description
                    entry.task = synthesized_entry.task or entry.task
                    entry.annotation_type = synthesized_entry.annotation_type or entry.annotation_type
                    entry.number_images = synthesized_entry.number_images or entry.number_images
                    entry.dimensions = synthesized_entry.dimensions or entry.dimensions
                    entry.repository = synthesized_entry.repository or entry.repository
                    
                    entry.rescrape_count += 1
                    entry.download_status = "pending" # Send back to classify
                    updated = True
                    print(f"✅ Synthesized metadata for {entry.title}")
                else:
                    print(f"⚠️ Agent failed to synthesize information for {entry.title}")
                    entry.rescrape_count += 1
    
    return {"sources": sources, "step_count": state["step_count"] + 1 if updated else state["step_count"]}
