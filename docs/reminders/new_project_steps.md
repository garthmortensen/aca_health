# New Project Setup Steps

TODO: Move this to codex project! edit codex alias to source and unload codex venv?

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
curl -LsSf https://astral.sh/uv/install.sh | sh

uv venv
source .venv/bin/activate
uv init
```

## 3. cz init

```bash
cz init
```

## 4. Final Setup Steps

```bash
git add .
cz commit

# create initial tag
git tag v0.1.0
```

## 5. Verification

```bash
python --version

cz version

uv pip list
```
