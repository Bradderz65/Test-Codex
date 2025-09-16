# Aurora Gallery

Aurora Gallery is a compact photo sharing website built with Flask. It lets multiple users register, log in, and upload images. Every upload is stored inside the Git repository so that commits can be pushed to GitHub for safekeeping, keeping the gallery in sync across restarts.

## Features

- 🔐 Account creation and login backed by hashed passwords.
- 🖼️ Image uploads (PNG, JPG, GIF, WEBP up to 10&nbsp;MB) with optional captions.
- 🗂️ Automatic organisation per user inside `static/uploads/`.
- 💾 Metadata persisted in `data/*.json` so the gallery repopulates after a restart.
- 🧹 Personal dashboard to review and delete the photos you've shared.
- 🪄 Minimal, animated UI designed for fast navigation.
- 🧬 Optional Git auto-commit and push so new photos land in GitHub.

## Getting started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the development server**

   ```bash
   flask --app app run --debug
   ```

   The site will be available at <http://127.0.0.1:5000/>.

3. **Create an account**

   Use the “Join” button to register your username and start uploading.

## GitHub sync

Uploads are stored within the repository so you can keep them under version control. By default the app will try to commit changes using the local Git installation. Configure the following environment variables before starting the server to customise the behaviour:

| Variable | Default | Description |
| --- | --- | --- |
| `ENABLE_GIT_SYNC` | `1` | Set to `0` to disable Git integration entirely. |
| `GIT_AUTO_PUSH` | `0` | Set to `1` to push commits automatically after they are created. |
| `GIT_REMOTE_NAME` | `origin` | Remote to push to when auto-push is enabled. |

Ensure that the repository has a configured remote and valid credentials (for example, a GitHub personal access token) if you enable auto-push.

> **Tip:** The first commit by the app might require Git user details. Configure them once with `git config user.name "Your Name"` and `git config user.email "you@example.com"` inside the repository.

## Project structure

```
app.py                # Flask application
requirements.txt      # Python dependencies
templates/            # Jinja templates
static/               # CSS, JS and uploaded files
  ├── css/style.css
  ├── js/app.js
  └── uploads/.gitkeep
data/                 # Persistent JSON storage
  ├── users.json
  └── photos.json
```

## Security notes

- Passwords are stored using Werkzeug’s secure hashing utilities. Even though they live in a JSON file, the hashes protect the raw credentials.
- Because uploads are committed to Git, avoid sharing sensitive imagery or personal data.

## License

This project is provided as-is for demonstration purposes. Feel free to adapt it to your needs.
