# New Project Setup Steps

## 1. git init

```bash
git init

echo "*.pyc
__pycache__/
.env
venv/
.uv/
dist/
build/
*.egg-info/
logs" > .gitignore

git add .
git commit -m "chore: initial commit"
```

## 2. uv

```bash
# install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

uv venv
source venv/bin/activate
uv init
```

## 3. cz init

```bash
cz init
```

### Commitizen Configuration Options:

When running `cz init`, you'll be prompted with these settings:

1. **Choose the type of project**: Select `Python`
2. **What is the name of the default branch?**: `main`
3. **Choose the schema of the commit message**: Select `conventional_commits`
4. **What is the name of the changelog file?**: `CHANGELOG.md`
5. **What is the increment in each tag?**: `$major.$minor.$patch$prerelease` (default)
6. **What is the starting version?**: `0.1.0`
7. **Choose the tag format**: `v$version` (adds 'v' prefix to tags)
8. **Enable pre-commit hook?**: `No`
9. **Enable commit-msg hook?**: `No`

## 4. Final Setup Steps

```bash
git add .
cz commit

# create initial tag
git tag v0.1.0
```

## 5. Verification

```bash
# Verify virtual environment
python --version

cz version

uv pip list
```
