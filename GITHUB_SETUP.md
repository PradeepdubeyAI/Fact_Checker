# GitHub Setup Guide

## ✅ Files Created

The following files have been created for GitHub:

1. **`.gitignore`** - Comprehensive ignore file for Python, Node.js, secrets, and temp files
2. **`LICENSE`** - MIT License for your project

## 📦 Prerequisites

You need to install Git for Windows first.

### Install Git

**Option 1: Using Winget (Recommended)**
```powershell
winget install --id Git.Git -e --source winget
```

**Option 2: Direct Download**
1. Download from: https://git-scm.com/download/win
2. Run the installer
3. Use default settings (recommended)
4. Restart your terminal after installation

**Option 3: GitHub Desktop (Easiest)**
1. Download from: https://desktop.github.com/
2. Install and sign in with your GitHub account
3. Click "Add" → "Add existing repository"
4. Browse to: `C:\Users\PradeepDubey\OneDrive - upGrad Education Private Limited\Desktop\upGrad_work\ClaimeAI-main`
5. Follow the GUI prompts to push to GitHub

## 🚀 Push to GitHub (After Installing Git)

### Step 1: Navigate to Your Project
```powershell
cd "C:\Users\PradeepDubey\OneDrive - upGrad Education Private Limited\Desktop\upGrad_work\ClaimeAI-main"
```

### Step 2: Configure Git (First Time Only)
```powershell
git config --global user.name "Pradeep Dubey"
git config --global user.email "your-email@example.com"
```

### Step 3: Initialize and Push to GitHub
```powershell
# Initialize git repository
git init

# Add all files (respects .gitignore)
git add .

# Check what will be committed
git status

# Create first commit
git commit -m "Initial commit: AI Fact-Checking System with multi-agent architecture"

# Set main branch
git branch -M main

# Add remote repository
git remote add origin https://github.com/PradeepdubeyAI/Fact_Checker.git

# Push to GitHub
git push -u origin main
```

## 📋 What Gets Pushed

### ✅ Included Files:
- All Python source code (`*.py`)
- README.md and ARCHITECTURE.md
- Project structure (`apps/` folder)
- Configuration files (except secrets)
- Documentation files

### ❌ Excluded Files (in .gitignore):
- `__pycache__/` - Python cache
- `.env` files - API keys and secrets
- `*.xlsx` - Generated Excel reports
- `*.mp4`, `*.avi`, `*.mov` - Test videos
- `node_modules/` - Node packages
- `.vscode/`, `.idea/` - IDE settings
- Test and debug files
- Temporary files and logs

## 🔒 Security Notes

### Protected Information (Not in Git):
1. **API Keys** - All `.env` files excluded
2. **Secrets.toml** - Streamlit secrets excluded
3. **Generated Reports** - Excel files excluded
4. **Test Data** - Videos and large files excluded

### Before Pushing:
✅ Verify no secrets in code:
```powershell
# Search for potential secrets
Select-String -Path . -Pattern "sk-proj|tvly-|api.*key.*=" -Recurse -Include *.py
```

✅ Check .gitignore is working:
```powershell
git status --ignored
```

## 🌐 After First Push

### Clone on Another Machine:
```bash
git clone https://github.com/PradeepdubeyAI/Fact_Checker.git
cd Fact_Checker
```

### Setup on New Machine:
1. Install Python 3.11+
2. Create `.env` file with API keys:
   ```
   OPENAI_API_KEY=your-key-here
   TAVILY_API_KEY=your-key-here
   ```
3. Install dependencies:
   ```bash
   cd apps/streamlit
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   streamlit run standalone_app.py
   ```

### Update Repository:
```powershell
# Pull latest changes
git pull origin main

# Make changes, then:
git add .
git commit -m "Describe your changes here"
git push origin main
```

## 🎯 Quick Commands Reference

```powershell
# Check status
git status

# See what changed
git diff

# View commit history
git log --oneline

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard all local changes
git reset --hard HEAD

# Create new branch
git checkout -b feature/new-feature

# Switch branches
git checkout main

# Merge branch into main
git checkout main
git merge feature/new-feature

# Delete branch
git branch -d feature/new-feature
```

## 💡 Tips

1. **Commit Often**: Make small, focused commits with clear messages
2. **Pull Before Push**: Always `git pull` before `git push` to avoid conflicts
3. **Use Branches**: Create feature branches for new work
4. **Review Before Commit**: Use `git status` and `git diff` before committing
5. **Descriptive Messages**: Write clear commit messages explaining what and why

## 📞 Need Help?

- Git Documentation: https://git-scm.com/doc
- GitHub Guides: https://guides.github.com/
- GitHub Desktop Help: https://docs.github.com/en/desktop

## 🔧 Troubleshooting

### "Permission denied" error:
```powershell
# Use HTTPS instead of SSH
git remote set-url origin https://github.com/PradeepdubeyAI/Fact_Checker.git
```

### Authentication required:
- GitHub now requires Personal Access Token instead of password
- Create token at: https://github.com/settings/tokens
- Use token as password when prompted

### Large file error:
```powershell
# Remove file from git
git rm --cached path/to/large-file

# Add to .gitignore
echo "path/to/large-file" >> .gitignore

# Commit the change
git commit -m "Remove large file"
```
