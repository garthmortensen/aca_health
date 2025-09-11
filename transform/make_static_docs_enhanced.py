"""
Enhanced Static dbt Documentation Generator for CI/CD

This script converts dbt's standard documentation into a single, self-contained HTML file
that works with or without a database connection. Optimized for GitHub Actions deployment.

Features:
- Works without database connection (using manifest only)
- Handles missing catalog.json gracefully
- Cleans up internal dbt packages
- Single file deployment ready for GitHub Pages
- Environment-aware (detects CI vs local)
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path

def get_project_root():
    """Find the dbt project root directory"""
    current = Path.cwd()
    # Look for dbt_project.yml in current or parent directories
    while current != current.parent:
        if (current / 'dbt_project.yml').exists():
            return current
        current = current.parent
    
    # Fall back to current directory if not found
    return Path.cwd()

def create_empty_catalog():
    """Create an empty catalog for when database connection isn't available"""
    return {
        "metadata": {
            "dbt_schema_version": "https://schemas.getdbt.com/dbt/catalog/v1.json",
            "dbt_version": "1.8.0",
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "invocation_id": "00000000-0000-0000-0000-000000000000",
            "env": {}
        },
        "nodes": {},
        "sources": {},
        "errors": None
    }

def clean_manifest(manifest, ignore_projects=None):
    """Remove internal dbt packages from manifest"""
    if ignore_projects is None:
        ignore_projects = ['dbt', 'dbt_utils', 'dbt_date', 'dbt_expectations']
    
    cleaned = manifest.copy()
    
    for element_type in ['nodes', 'sources', 'macros', 'parent_map', 'child_map']:
        if element_type in cleaned:
            # Create a new dict to avoid modifying during iteration
            original_dict = cleaned[element_type].copy()
            cleaned[element_type] = {}
            
            for key, value in original_dict.items():
                # Keep items that don't match any ignored project patterns
                keep_item = True
                for ignore_project in ignore_projects:
                    if re.match(fr'^.*\.{ignore_project}\.', key):
                        keep_item = False
                        break
                
                if keep_item:
                    cleaned[element_type][key] = value
    
    return cleaned

def generate_static_docs():
    """Generate static dbt documentation"""
    
    # Detect environment
    is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
    print(f"Running in {'CI' if is_ci else 'local'} environment")
    
    # Get project paths
    project_root = get_project_root()
    target_dir = project_root / 'target'
    
    print(f"Project root: {project_root}")
    print(f"Target directory: {target_dir}")
    
    # Check if target directory exists
    if not target_dir.exists():
        raise FileNotFoundError(f"Target directory not found: {target_dir}")
    
    # File paths
    index_html_path = target_dir / 'index.html'
    manifest_path = target_dir / 'manifest.json'
    catalog_path = target_dir / 'catalog.json'
    
    # Check required files
    if not index_html_path.exists():
        raise FileNotFoundError(f"index.html not found. Run 'dbt docs generate' first.")
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found. Run 'dbt docs generate' first.")
    
    # Read the HTML template
    print("Reading index.html...")
    with open(index_html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Read manifest
    print("Reading manifest.json...")
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.loads(f.read())
    
    # Clean the manifest
    print("Cleaning manifest (removing internal dbt packages)...")
    cleaned_manifest = clean_manifest(manifest)
    
    # Read or create catalog
    if catalog_path.exists():
        print("Reading existing catalog.json...")
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.loads(f.read())
    else:
        print("catalog.json not found, creating empty catalog (no database connection)")
        catalog = create_empty_catalog()
    
    # JavaScript pattern to replace
    # This is the pattern dbt uses to load external JSON files
    search_patterns = [
        'o=[i("manifest","manifest.json"+t),i("catalog","catalog.json"+t)]',
        'o=[i("manifest","manifest.json"+a),i("catalog","catalog.json"+a)]',
        # Alternative patterns that might appear in different dbt versions
        r'o=\[i\("manifest","manifest\.json"\+[a-z]\),i\("catalog","catalog\.json"\+[a-z]\)\]'
    ]
    
    # Create the replacement string with embedded JSON
    replacement = f"o=[{{label: 'manifest', data: {json.dumps(cleaned_manifest)}}},{{label: 'catalog', data: {json.dumps(catalog)}}}]"
    
    # Try to replace the pattern
    replaced = False
    new_content = html_content
    
    for pattern in search_patterns:
        if re.search(pattern, html_content):
            new_content = re.sub(pattern, replacement, html_content)
            replaced = True
            print(f"Replaced pattern: {pattern}")
            break
    
    if not replaced:
        print("WARNING: Could not find expected JavaScript pattern in HTML file.")
        print("The documentation might not work correctly.")
        # Try a more generic approach
        if 'manifest.json' in html_content and 'catalog.json' in html_content:
            print("Attempting generic replacement...")
            # This is a fallback that might work
            new_content = html_content.replace('"manifest.json"', '"manifest"').replace('"catalog.json"', '"catalog"')
            new_content = f'<script>window.dbtDocsManifest = {json.dumps(cleaned_manifest)}; window.dbtDocsCatalog = {json.dumps(catalog)};</script>\n' + new_content
    
    # Write the modified HTML
    print("Writing static documentation...")
    with open(index_html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # Generate summary
    model_count = len(cleaned_manifest.get('nodes', {}).keys())
    source_count = len(cleaned_manifest.get('sources', {}).keys())
    macro_count = len(cleaned_manifest.get('macros', {}).keys())
    
    print("=" * 60)
    print("Static dbt Documentation Generated Successfully!")
    print("=" * 60)
    print(f"Output file: {index_html_path}")
    print(f"Models: {model_count}")
    print(f"Sources: {source_count}")
    print(f"Macros: {macro_count}")
    print(f"Environment: {'CI/CD' if is_ci else 'Local'}")
    print(f"Catalog: {'Database connected' if catalog_path.exists() else 'Empty (no connection)'}")
    print("=" * 60)
    print("Ready for deployment to GitHub Pages!")

if __name__ == "__main__":
    try:
        generate_static_docs()
    except Exception as e:
        print(f"ERROR: {str(e)}")
        exit(1)
