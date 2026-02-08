# Streamlit Cloud Deployment Guide

## 🚀 Quick Deployment Steps

### Step 1: Prepare Your Repository

✅ **Already Done:**
- ✅ Code pushed to GitHub: https://github.com/PradeepdubeyAI/Fact_Checker
- ✅ `.gitignore` configured (API keys excluded)
- ✅ `requirements.txt` present

### Step 2: Sign Up for Streamlit Cloud

1. **Go to Streamlit Cloud**: https://share.streamlit.io/
2. **Click "Sign up"** or **"Get started"**
3. **Authenticate with GitHub** (recommended)
   - This gives Streamlit access to your repositories
4. **Authorize Streamlit** to access your GitHub account

### Step 3: Deploy Your App

1. **Click "New app"** button (top right)

2. **Fill in deployment settings:**
   ```
   Repository: PradeepdubeyAI/Fact_Checker
   Branch: main
   Main file path: apps/streamlit/standalone_app.py
   ```

3. **Advanced settings** (click on it):
   - **Python version**: 3.11 (or 3.12)
   - Keep other defaults

4. **Click "Deploy"**
   - First deployment takes 3-5 minutes
   - Streamlit will install all dependencies

### Step 4: Configure Secrets (API Keys)

🔐 **Important:** Your app needs API keys to work!

1. **Go to your deployed app dashboard**
2. **Click the "⋮" menu** (three dots, top right)
3. **Select "Settings"**
4. **Navigate to "Secrets" section**
5. **Add your secrets in TOML format:**

```toml
# Paste this in the Secrets section
OPENAI_API_KEY = "sk-proj-your-actual-openai-key-here"
TAVILY_API_KEY = "tvly-your-actual-tavily-key-here"
```

6. **Click "Save"**
7. **App will automatically reboot** with secrets loaded

### Step 5: Test Your Deployed App

1. **Wait for app to finish deploying** (status shows "Running")
2. **Click on your app URL** (e.g., `https://yourapp.streamlit.app`)
3. **Test all features:**
   - ✅ Full Text Analysis mode
   - ✅ Single Fact Verification mode
   - ✅ Claim Extraction Only mode
   - ✅ Video Fact-Checking mode
   - ✅ Excel export

## 📋 Pre-Deployment Checklist

Before deploying, verify these files exist in your repo:

```
✅ apps/streamlit/standalone_app.py    (main app)
✅ apps/streamlit/requirements.txt     (dependencies)
✅ apps/streamlit/export_excel.py      (Excel export)
✅ apps/agent/                         (all agent code)
✅ .gitignore                          (excludes secrets)
```

## 🔧 Create a Root-Level requirements.txt (Required)

Streamlit Cloud needs a `requirements.txt` at the **repository root**.

**Create this file:**

```bash
cd "C:\Users\PradeepDubey\OneDrive - upGrad Education Private Limited\Desktop\upGrad_work\ClaimeAI-main"
```

Then run these commands in PowerShell:
```powershell
# Copy streamlit requirements to root
Copy-Item apps\streamlit\requirements.txt requirements.txt

# Commit and push
git add requirements.txt
git commit -m "Add root requirements.txt for Streamlit Cloud deployment"
git push origin main
```

## 📝 Alternative: Create packages.txt (For System Dependencies)

If your app needs system packages (unlikely for this project), create `packages.txt`:

```
ffmpeg
```

## 🌐 Your App URLs

After deployment, you'll get:

- **App URL**: `https://fact-checker-pradeepdubey.streamlit.app`
- **Dashboard**: `https://share.streamlit.io/`

## ⚙️ Streamlit Cloud Settings

### Recommended Settings:

**Python Version:** 3.11 or 3.12
**Resources:** Free tier (sufficient for testing)
  - 1 GB RAM
  - 800 MB storage
  - Shared CPU

**Custom Domain** (optional):
- Available in paid plans
- Can set up custom subdomain

## 🔄 Updating Your Deployed App

Streamlit Cloud **auto-deploys** when you push to GitHub:

```powershell
# Make changes to your code
# Then push:
git add .
git commit -m "Description of changes"
git push origin main

# Streamlit Cloud will automatically redeploy (takes 1-2 minutes)
```

### Manual Reboot:
1. Go to app dashboard
2. Click "⋮" → **"Reboot app"**

## 🐛 Troubleshooting

### Issue 1: "ModuleNotFoundError"

**Solution:** Ensure `requirements.txt` has all dependencies:
```text
streamlit==1.36.0
langchain==0.3.0
langchain-openai==0.2.0
langgraph==0.3.0
tavily-python==0.5.0
openpyxl==3.1.5
moviepy==1.0.3
openai==1.50.0
pydantic==2.9.0
python-dotenv==1.0.1
```

### Issue 2: "API Keys Not Working"

**Solution:** 
- Check secrets are saved correctly (no extra spaces)
- Format must be: `KEY_NAME = "value"`
- Reboot app after adding secrets

### Issue 3: "Import Error from apps.agent"

**Solution:** Add this at the top of `standalone_app.py` (already done):
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))
```

### Issue 4: "File Not Found"

**Solution:** Use relative paths:
```python
agent_path = os.path.join(os.path.dirname(__file__), '..', 'agent')
```

### Issue 5: App Crashes or Times Out

**Solution:**
- Free tier has resource limits
- Large video files may timeout
- Consider upgrading to paid tier for production

## 📊 Monitoring Your App

### View Logs:
1. Go to app dashboard
2. Click "⋮" → **"Logs"**
3. See real-time logs and errors

### Analytics:
- View visitor count
- Track app usage
- Monitor performance

## 💰 Pricing

**Free Tier:**
- ✅ **Unlimited** public apps
- ✅ 1 GB RAM per app
- ✅ Auto-sleep after inactivity
- ✅ Community support

**Paid Tiers:** (Optional)
- More resources
- Private apps
- Custom domains
- Priority support

## 🔒 Security Best Practices

### ✅ Do's:
- ✅ Use Streamlit Secrets for API keys
- ✅ Keep `.gitignore` updated
- ✅ Never commit `.env` files
- ✅ Use environment variables

### ❌ Don'ts:
- ❌ Don't hardcode API keys in code
- ❌ Don't commit secrets to GitHub
- ❌ Don't expose secrets in logs
- ❌ Don't share secret URLs publicly

## 🎯 Post-Deployment Checklist

After successful deployment:

- [ ] Test all 4 operation modes
- [ ] Verify API keys work correctly
- [ ] Test video upload (small file first)
- [ ] Try Excel export download
- [ ] Check metrics tracking
- [ ] Test multi-language support
- [ ] Share app URL with users
- [ ] Monitor logs for errors
- [ ] Set up custom domain (optional)
- [ ] Enable analytics (optional)

## 📞 Support Resources

- **Streamlit Docs**: https://docs.streamlit.io/
- **Streamlit Cloud Docs**: https://docs.streamlit.io/streamlit-community-cloud
- **Community Forum**: https://discuss.streamlit.io/
- **GitHub Issues**: https://github.com/streamlit/streamlit/issues

## 🚨 Common Errors and Solutions

### Error: "App crashed!"

**Check:**
1. Logs for specific error
2. All imports working
3. Secrets configured
4. requirements.txt complete

### Error: "This app has gone to sleep"

**Normal behavior** - Free tier apps sleep after inactivity.
**Solution:** Just click to wake it up!

### Error: "Resource limits exceeded"

**Cause:** Large file processing or too many concurrent users
**Solution:** 
- Optimize code
- Reduce file sizes
- Upgrade to paid tier

## 🎉 Success!

Once deployed, your app will be available 24/7 at:
`https://your-app-name.streamlit.app`

Share this URL with anyone to use your AI Fact-Checker! 🌟

---

## Quick Command Reference

```powershell
# Navigate to project
cd "C:\Users\PradeepDubey\OneDrive - upGrad Education Private Limited\Desktop\upGrad_work\ClaimeAI-main"

# Copy requirements to root
Copy-Item apps\streamlit\requirements.txt requirements.txt

# Commit and push
git add requirements.txt
git commit -m "Add requirements.txt for Streamlit Cloud"
git push origin main

# Update app (after making changes)
git add .
git commit -m "Update: your changes"
git push origin main
```
