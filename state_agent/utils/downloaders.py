import os
import subprocess
import requests
import kagglehub
from huggingface_hub import snapshot_download
from typing import Optional

def download_kaggle(handle: str, download_dir: str = "./data/downloads/kaggle") -> str:
    """
    Download a Kaggle dataset using kagglehub.
    """
    print(f"📥 Downloading Kaggle dataset: {handle}")
    os.makedirs(download_dir, exist_ok=True)
    path = kagglehub.dataset_download(handle, output_dir=os.path.join(download_dir, handle.split("/")[-1]))
    return path

def download_github(repo_url: str, download_dir: str = "./data/downloads/github") -> str:
    """
    Download a GitHub repository using git clone.
    """
    print(f"📥 Downloading GitHub repo: {repo_url}")
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    target_path = os.path.join(download_dir, repo_name)
    
    if os.path.exists(target_path):
        print(f"Found existing repo at {target_path}, pulling latest...")
        subprocess.run(["git", "-C", target_path, "pull"], check=True)
    else:
        os.makedirs(download_dir, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", repo_url, target_path], check=True)
    
    return target_path

def download_huggingface(repo_id: str, download_dir: str = "./data/downloads/huggingface") -> str:
    """
    Download a HuggingFace dataset or model using snapshot_download.
    """
    print(f"📥 Downloading HuggingFace repo: {repo_id}")
    target_path = os.path.join(download_dir, repo_id.replace("/", "--"))
    os.makedirs(target_path, exist_ok=True)
    
    path = snapshot_download(repo_id=repo_id, local_dir=target_path, local_dir_use_symlinks=False)
    return path

def download_generic(url: str, download_dir: str = "./data/downloads/generic") -> str:
    """
    Download a file from a generic URL.
    """
    print(f"📥 Downloading from URL: {url}")
    os.makedirs(download_dir, exist_ok=True)
    filename = url.split("/")[-1]
    if not filename or "." not in filename:
        filename = "downloaded_file"
        
    target_path = os.path.join(download_dir, filename)
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(target_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            
    return target_path

def download_dataset(source_type: str, identifier: str, download_dir: Optional[str] = None) -> Optional[str]:
    """
    Unified entry point for downloading datasets based on type.
    """
    try:
        if source_type == "kaggle":
            return download_kaggle(identifier, download_dir or "./data/downloads/kaggle")
        elif source_type == "github":
            return download_github(identifier, download_dir or "./data/downloads/github")
        elif source_type == "huggingface":
            return download_huggingface(identifier, download_dir or "./data/downloads/huggingface")
        elif source_type == "direct_link":
            return download_generic(identifier, download_dir or "./data/downloads/generic")
        else:
            print(f"⚠️ Unknown source type: {source_type}")
            return None
    except Exception as e:
        print(f"❌ Error downloading {identifier}: {e}")
        return None
