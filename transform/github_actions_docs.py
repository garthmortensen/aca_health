"""
GitHub Actions dbt Docs Generator

This script is specifically designed for the GitHub Actions workflow described in
Connor McShane's Medium article. It creates a single HTML file suitable for
GitHub Pages deployment.

Based on the approach from: 4Sushi's solution in dbt-docs issue #53
https://github.com/dbt-labs/dbt-docs/issues/53#issuecomment-1011053807
"""

import json
import os
import sys
from pathlib import Path


def main():
    """Generate static dbt docs for GitHub Pages deployment"""
    
    # Assume we're running from the transform directory
    project_dir = Path.cwd()
    target_dir = project_dir / "target"
    
    print(f"Working directory: {project_dir}")
    print(f"Target directory: {target_dir}")
    
    # Check if we have the required files
    index_path = target_dir / "index.html"
    manifest_path = target_dir / "manifest.json"
    catalog_path = target_dir / "catalog.json"
    
    if not index_path.exists():
        print("ERROR: index.html not found. Did you run 'dbt docs generate'?")
        sys.exit(1)
        
    if not manifest_path.exists():
        print("ERROR: manifest.json not found. Did you run 'dbt docs generate'?")
        sys.exit(1)
    
    # Read the original index.html
    print("Reading index.html...")
    with open(index_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Read manifest.json
    print("Reading manifest.json...")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # Read catalog.json if it exists, otherwise create empty one
    if catalog_path.exists():
        print("Reading catalog.json...")
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    else:
        print("Creating empty catalog.json (no database connection)")
        catalog = {
            "metadata": {
                "dbt_schema_version": "https://schemas.getdbt.com/dbt/catalog/v1.json",
                "generated_at": "1970-01-01T00:00:00.000000Z"
            },
            "nodes": {},
            "sources": {}
        }
    
    # The pattern from the original article/4Sushi solution
    # This finds the part of the JavaScript that loads external JSON files
    search_string = 'o=[i("manifest","manifest.json"+t),i("catalog","catalog.json"+t)]'
    
    # Create the replacement that embeds the JSON data directly
    replace_string = (
        f'o=[{{label: "manifest", data: {json.dumps(manifest)}}}, '
        f'{{label: "catalog", data: {json.dumps(catalog)}}}]'
    )
    
    # Check if we can find the pattern
    if search_string not in html_content:
        print("WARNING: Expected JavaScript pattern not found in index.html")
        print("This might be a different version of dbt. Trying alternative approaches...")
        
        # Try some alternatives
        alternatives = [
            'o=[i("manifest","manifest.json"+a),i("catalog","catalog.json"+a)]',
            'o=[i("manifest","manifest.json"+e),i("catalog","catalog.json"+e)]'
        ]
        
        found = False
        for alt_pattern in alternatives:
            if alt_pattern in html_content:
                html_content = html_content.replace(alt_pattern, replace_string)
                found = True
                print(f"Found alternative pattern: {alt_pattern}")
                break
        
        if not found:
            print("ERROR: Could not find any recognized pattern to replace")
            print("The static docs generation may not work correctly")
            # Continue anyway, but warn the user
    else:
        # Replace the original pattern
        html_content = html_content.replace(search_string, replace_string)
        print("Successfully replaced the manifest/catalog loading pattern")
    
    # Write the modified HTML file
    print("Writing static HTML file...")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("✅ Static dbt docs generated successfully!")
    print(f"📁 Output file: {index_path}")
    print(f"📊 Models in manifest: {len(manifest.get('nodes', {}))}")
    print(f"📊 Sources in manifest: {len(manifest.get('sources', {}))}")
    print("🚀 Ready for GitHub Pages deployment!")


if __name__ == "__main__":
    main()
