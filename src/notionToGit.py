import os
import csv
import requests
import markdown
import frontmatter
import json
from notion_client import Client
from git import Repo

# Load configuration file
def load_config(config_path="config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

# Initialize Notion client
notion = Client(auth=CONFIG["NOTION_API_KEY"])

def fetch_notion_page(page_id):
    """Fetch page content from Notion API"""
    response = notion.blocks.children.list(block_id=page_id)
    return response["results"]

def download_image(url, image_dir, filename):
    """Download and save image"""
    os.makedirs(image_dir, exist_ok=True)
    image_path = os.path.join(image_dir, filename)
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(image_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        return image_path
    return None

def convert_to_markdown(notion_data, image_dir):
    """Convert Notion data to Markdown (including images)"""
    md_content = ""
    for block in notion_data:
        if block["type"] == "paragraph":
            md_content += block["paragraph"]["rich_text"][0]["plain_text"] + "\n\n"
        elif block["type"] == "image":
            image_url = block["image"]["file"]["url"]
            image_filename = os.path.basename(image_url.split("?")[0])
            image_path = download_image(image_url, image_dir, image_filename)
            if image_path:
                md_content += f"![{image_filename}]({image_dir}/{image_filename})\n\n"
    return md_content

def save_to_markdown_file(md_content, filename):
    """Save content as a Markdown file"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md_content)

def push_to_github():
    """Push changes to GitHub repository"""
    repo = Repo(CONFIG["GITHUB_REPO_PATH"])
    repo.git.add(A=True)
    repo.index.commit("Automated sync from Notion with images")
    origin = repo.remote(name='origin')
    origin.push()

def process_notion_pages():
    """Read CSV file and process each Notion page"""
    with open(CONFIG["CSV_FILE_PATH"], newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            page_id, filename = row
            """Create an image directory with the same name as the file"""
            image_dir = os.path.splitext(filename)[0]  
            notion_data = fetch_notion_page(page_id)
            md_content = convert_to_markdown(notion_data, image_dir)
            save_to_markdown_file(md_content, filename)
    push_to_github()

def main():
    """Main function to start the process"""
    process_notion_pages()

if __name__ == "__main__":
    main()
