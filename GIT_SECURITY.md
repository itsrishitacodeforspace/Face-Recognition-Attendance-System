# Sensitive Files & Git Security Guide

## Quick Reference

### ✅ What's Protected
- `backend/.env` - Backend secrets (SECRET_KEY, database credentials)
- `frontend/.env` - Frontend API configuration  
- `*.db`, `*.sqlite` - Local databases
- `backend/data/models/` - ML embeddings and model caches
- `.venv/`, `node_modules/` - Virtual environments and dependencies
- `*.log` - Log files
- `*.key`, `*.pem` - Private keys and certificates
- IDE config (`.vscode/`, `.idea/`)
- OS files (`.DS_Store`, `Thumbs.db`)

### ⚠️ Most Important

**NEVER add to git:**
```
.env files with secrets
Private keys (*.key, *.pem, id_rsa)
Database credentials in code
API keys and tokens
Docker compose override files with secrets
```

**ALWAYS add to git:**
```
.env.example templates
SECURITY.md documentation
docker-compose.yml (with placeholders)
README.md setup instructions
.gitignore itself
```

## Local Setup (First Time)

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env with your local values
nano .env

# Frontend  
cd ../frontend
cp .env.example .env
# Edit .env with your local values
nano .env

# Verify setup
cd ..
git status  # Should NOT show .env files
```

## Before Committing

**Quick checklist:**
```bash
# 1. Check no secrets are staged
git diff --cached | grep -i "password\|secret\|api_key\|token" && echo "⚠️ SECRETS FOUND!" || echo "✅ No obvious secrets"

# 2. Verify .env files are ignored
git check-ignore -v backend/.env frontend/.env && echo "✅ .env properly ignored" || echo "⚠️ WARNING!"

# 3. List what will be committed
git diff --cached --name-only

# 4. If all looks good, commit
git commit -m "Your message"
```

## Common Mistakes

### ❌ Accidentally added `.env`?
```bash
# Remove from git history
git rm --cached backend/.env
git commit --amend
git push origin <branch> --force-with-lease  # Only if not pushed to main yet!
```

### ❌ Committed a secret?
```bash
# Use git-filter-branch or BFG (see SECURITY.md for details)
# This is a serious issue - notify team immediately!
```

### ❌ Forgot to .gitignore something?
```bash
# Add pattern to .gitignore
echo "*.important" >> .gitignore
git add .gitignore
git commit -m "Add *.important to gitignore"
```

## Development Workflows

### GitHub Actions / CI-CD
Environment secrets should be stored as **repository secrets**, not in code:

1. Go to repository Settings → Secrets and variables → Actions
2. Add secrets there (never in `.env` files)
3. Reference in workflows:
   ```yaml
   - name: Deploy
     env:
       SECRET_KEY: ${{ secrets.SECRET_KEY }}
       DATABASE_URL: ${{ secrets.DATABASE_URL }}
   ```

### Docker / Compose
For production Docker deployments:
```yaml
# docker-compose.yml (template - committed to git)
services:
  backend:
    environment:
      - SECRET_KEY=${SECRET_KEY}

# .env file (local override - NOT committed)
SECRET_KEY=your-actual-secret-key
```

## Testing Gitignore Rules

```bash
# Check if file would be ignored
git check-ignore -v backend/.env

# See all ignored files
git status --ignored

# Test a pattern
git check-ignore -v -x "*.secret"

# Find untracked files that SHOULD be ignored
git ls-files --others --exclude-standard | head -10
```

## Automated Secret Detection (Optional)

### Pre-commit Hook (Recommended)
```bash
# Install
pip install pre-commit gitleaks

# Configure
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        stages: [commit]
EOF

# Setup
pre-commit install
pre-commit run --all-files

# This will now run before every commit
```

## Emergency: Exposed Secret

If you accidentally commit a secret:

1. **Immediately rotate the secret** (generate new key/password/token)
2. **Notify your team lead**
3. **Remove from git history:**
   ```bash
   # Option 1: BFG (simpler, recommended)
   bfg --delete-files backend/.env
   git reflog expire --expire=now --all && git gc --prune=now
   
   # Option 2: git-filter-branch (more control)
   git filter-branch --tree-filter 'rm -f backend/.env' HEAD
   ```
4. **Force push only if not merged to main:**
   ```bash
   git push origin <branch> --force-with-lease
   ```
5. **Document in incident log**

## File Size Limits

To prevent accidentally committing large files:
```bash
# Check for large files
find . -size +10M -type f | grep -v node_modules | grep -v .venv

# Add to .gitignore if needed
echo "*.large_file" >> .gitignore
```

## Useful Commands

```bash
# Show all patterns in .gitignore
git config --global core.excludesFile ~/.gitignore_global
cat .gitignore

# Verify nothing sensitive is staged
git diff --cached --stat

# See what would be committed
git diff --cached

# Check git history for secrets (safe, reads local history only)
git log -S "password" --source --all --oneline

# Show most recently modified files
git log --name-status -5
```

## Related Documentation

- [SECURITY.md](SECURITY.md) - Full security guide
- [.gitignore-audit.md](.gitignore-audit.md) - Detailed audit report
- [.env.example](backend/.env.example) - Backend environment template
- [frontend/.env.example](frontend/.env.example) - Frontend environment template

---

**Last Updated**: March 28, 2026  
**Status**: ✅ All sensitive files protected
