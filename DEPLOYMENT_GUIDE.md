# 🚀 Miniploy - Simple Deployment CLI

One-stop AI-powered deployment to Render, Fly.io, Vercel, Railway, Netlify.

## ✅ What's Fixed

- ✅ All platform authentication now auto-fetches required IDs (owner, workspace, org)
- ✅ Groq AI integration working (loads from `.env`)
- ✅ New `miniploy static` command for instant static file deployment
- ✅ Interactive token management with `miniploy tokens`
- ✅ Better error handling across all platforms

## 🎯 Quick Start - Deploy Static HTML to Vercel

### 1. Install (if not already done)
```bash
pip install -e .
```

### 2. Add Your Vercel Token
```bash
# Option 1: Use the interactive command
miniploy tokens vercel

# Option 2: Add to .env file
echo "VERCEL_TOKEN=your_token_here" >> .env
```

Get token from: https://vercel.com/account/settings/tokens

### 3. Deploy Your Static Site
```bash
# Deploy the test static site
miniploy static ./test-static

# Or deploy your own static files
miniploy static ./my-site --name my-awesome-site
```

That's it! Your site will be live in seconds! 🎉

## 📋 All Available Commands

| Command | Description |
|---------|-------------|
| `miniploy tokens` | Interactive token management (add/view tokens) |
| `miniploy tokens vercel` | Add Vercel token |
| `miniploy tokens all` | Add tokens for all platforms |
| `miniploy static <dir>` | Deploy static files to Vercel instantly |
| `miniploy setup <platform>` | Setup platform (creates project) |
| `miniploy deploy` | AI-powered project analysis |
| `miniploy run` | Deploy to configured platform |

## 🔐 Managing Tokens

### Interactive Menu
```bash
miniploy tokens
```

### Add Specific Platform
```bash
miniploy tokens vercel
miniploy tokens netlify
miniploy tokens render
miniploy tokens railway
miniploy tokens flyio
```

### Add All Platforms at Once
```bash
miniploy tokens all
```

## 🌐 Platform-Specific Features

### Vercel
- ✅ Static file deployment (instant)
- ✅ Project creation
- ✅ Environment variables
- Get token: https://vercel.com/account/settings/tokens

### Netlify
- ✅ Site creation
- ✅ Auto-detects account
- Get token: https://app.netlify.com/user/applications/personal

### Render
- ✅ Static site creation
- ✅ Auto-fetches owner ID
- Get token: https://dashboard.render.com/u/settings?add-api-key

### Railway
- ✅ Project creation
- ✅ Auto-fetches workspace/team ID
- Get token: https://railway.com/account/tokens

### Fly.io
- ✅ App creation
- ✅ Auto-fetches organization
- Get token: https://fly.io/user/personal_access_tokens

## 🤖 AI-Powered Deployment

```bash
# Analyze your project and get smart deployment suggestions
miniploy deploy --auto

# This will:
# 1. Detect your framework (Next.js, React, Flask, etc.)
# 2. Suggest build commands
# 3. Recommend best platform
# 4. Create miniploy.yaml config
```

**Note**: Requires `GROQ_API_KEY` in your `.env` file.  
Get it from: https://console.groq.com

## 📁 Project Structure

```
miniploy/
├── src/miniploy/
│   ├── commands/
│   │   ├── tokens.py     # Token management
│   │   ├── static.py     # Static deployment
│   │   ├── setup.py      # Platform setup
│   │   ├── deploy.py     # AI analysis
│   │   └── run.py        # Deploy execution
│   ├── platforms/
│   │   ├── vercel.py     # Vercel API
│   │   ├── netlify.py    # Netlify API
│   │   ├── render.py     # Render API
│   │   ├── railway.py    # Railway GraphQL
│   │   └── flyio.py      # Fly.io GraphQL
│   └── ai/
│       └── analyzer.py   # Groq AI integration
├── test-static/          # Example static site
│   └── index.html
└── .env                  # Your API tokens (NEVER commit!)
```

## 🔒 Security

- ✅ `.env` file is in `.gitignore` - your tokens are safe
- ✅ Tokens stored locally, never sent anywhere except the respective platforms
- ✅ Password-masked input when entering tokens

## 🐛 Troubleshooting

### "Token not found"
```bash
# Add token using interactive menu
miniploy tokens

# Or add directly to .env
echo "VERCEL_TOKEN=your_token" >> .env
```

### "Authentication failed"
- Verify your token is correct
- Check token hasn't expired
- Ensure token has correct permissions

### "No files found to deploy"
- Make sure you're in the right directory
- Check that files aren't hidden or in ignored folders

## 💡 Examples

### Deploy a Simple HTML Page
```bash
# Create a directory
mkdir my-site
echo "<h1>Hello World!</h1>" > my-site/index.html

# Deploy it
miniploy static ./my-site
```

### Deploy with Custom Name
```bash
miniploy static ./my-portfolio --name john-portfolio-2024
```

### Full Workflow (Complex App)
```bash
# 1. Add tokens
miniploy tokens vercel

# 2. Analyze project
miniploy deploy --auto

# 3. Setup platform
miniploy setup vercel

# 4. Deploy
miniploy run
```

## 🌟 Features

- 🤖 AI-powered framework detection
- 🚀 Instant static file deployment
- 🔐 Secure token management
- 📊 Beautiful CLI interface
- 🌍 Multi-platform support
- 💜 Open source

## 📝 Environment Variables

Required in `.env`:

```env
# Platform Tokens (add the ones you need)
VERCEL_TOKEN=your_vercel_token
NETLIFY_TOKEN=your_netlify_token
RENDER_TOKEN=your_render_token
RAILWAY_TOKEN=your_railway_token
FLY_API_TOKEN=your_fly_token

# Optional: For AI-powered analysis
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama3-70b-8192
```

## 🎉 Try It Now!

```bash
# Deploy the included test page
miniploy static ./test-static

# Should output:
# ✅ Deployment successful!
# 🌐 Visit your site: https://your-site.vercel.app
```

---

Made with 💜 by the Miniploy team
