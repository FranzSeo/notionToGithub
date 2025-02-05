import os
import csv
import requests
import markdown
import frontmatter
import json
import re
from notion_client import Client
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

# Load configuration file
def load_config(config_path="./src/config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

# Initialize Notion client
notion = Client(auth=CONFIG["NOTION_API_KEY"])

def is_valid_uuid(uuid_str):
    """Check if the given string is a valid UUID format"""
    uuid_regex = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.IGNORECASE)
    return bool(uuid_regex.match(uuid_str))

def fix_notion_id(notion_id):
    """Attempt to convert a 32-character Notion ID to UUID format"""
    original_id = notion_id
    notion_id = notion_id.replace("-", "")
    if len(notion_id) == 32:
        notion_id = f"{notion_id[:8]}-{notion_id[8:12]}-{notion_id[12:16]}-{notion_id[16:20]}-{notion_id[20:]}"
    print(f"[DEBUG] Converted Notion ID: {original_id} -> {notion_id}")
    return notion_id

def fetch_notion_page(page_id):
    """Fetch page content from Notion API"""
    page_id = fix_notion_id(page_id)
    if not is_valid_uuid(page_id):
        raise ValueError(f"Invalid Notion Page ID: {page_id}. Please check your configuration.")
    try:
        print(f"[DEBUG] Fetching Notion Page ID: {page_id}")
        page = notion.pages.retrieve(page_id=page_id)
        print(f"[DEBUG] Page retrieved successfully: {page}")
        response = notion.blocks.children.list(block_id=page_id)
        return response["results"]
    except Exception as e:
        print(f"[ERROR] Could not retrieve Notion page. Error: {e}")
        raise ValueError(f"Error retrieving Notion page: {e}")

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
        if block["type"] == "paragraph" and block["paragraph"].get("rich_text"):
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

def process_selected_notion_pages():
    """Retrieve only selected pages from Notion workspace based on CSV file"""
    with open(CONFIG["CSV_FILE_PATH"], newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            page_id, filename = row
            page_id = fix_notion_id(page_id)
            if not is_valid_uuid(page_id):
                print(f"Skipping invalid Notion Page ID: {page_id}")
                continue
            image_dir = os.path.splitext(filename)[0]
            notion_data = fetch_notion_page(page_id)
            md_content = convert_to_markdown(notion_data, image_dir)
            save_to_markdown_file(md_content, filename)

def main():
    """Main function to start the process"""
    process_selected_notion_pages()

if __name__ == "__main__":
    main()
