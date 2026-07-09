# CrexiFy TV Decrypted API Pipeline

This repository hosts the automated decryption pipeline for **CrexiFy TV_v1.0** configurations, including `app.txt`, `event_cats.txt`, `events.txt`, and dynamic match stream files (`pro/*.txt`).

---

## Architecture Overview

1. **`app_control.json`**: Holds the decryption AES keys (`Crexify_SetB` / `Crexify_SetA`) and the target source configurations.
2. **`fetch_fresh.py`**: The primary runner script that:
   - Fetches the remote encrypted configs from `https://crex-api.pages.dev/`.
   - Decrypts `app.txt` using **Set B** (Direct AES-CBC).
   - Decrypts `event_cats.txt` and `events.txt` using **Set A** (V2 Preprocess + AES-CBC).
   - Resolves all dynamic pro event paths (`pro/...txt`) listed in the events database, downloads them, decrypts them using **Set B**, and writes the decrypted stream options.
   - Redirects all API gateway URLs dynamically to your custom GitHub Pages branch.
   - Outputs the complete structure to the `decrypted_output/` folder.

---

## Setup & Running

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Decryption Runner
```bash
python fetch_fresh.py
```

All decrypted endpoints will be populated in the `decrypted_output/` directory, mirroring the app's structure.

---

## GitHub Actions & GitHub Pages Deployment

To automatically run this script on a cron schedule (e.g., every 5 minutes) and host the decrypted endpoints on GitHub Pages:

1. Create a `.github/workflows/fetch_api.yml` workflow file.
2. Set up the workflow to:
   - Check out the repository.
   - Install Python and dependencies.
   - Run `python fetch_fresh.py`.
   - Commit and push the `decrypted_output/` folder to the `gh-pages` branch.
3. Configure your GitHub repository settings to serve Pages from the `gh-pages` branch.
