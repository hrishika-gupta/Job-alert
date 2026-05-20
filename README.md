# 📚 Daily Education Internship Alert

Sends a daily email at **8 AM IST** with new internship listings for:
- Curriculum Design Intern
- Instructional Design Intern
- Research & Development Intern (Education)

Sources: **LinkedIn**, **Indeed (India)**, **Remotive**

---

## Setup (5 minutes)

### 1. Fork / push this repo to GitHub
Create a new **private** GitHub repo and push these files.

### 2. Create a Gmail App Password
> You need a Google account with 2FA enabled.

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. App name: `job-alert` → click **Create**
3. Copy the 16-character password shown (e.g. `abcd efgh ijkl mnop`)

### 3. Add GitHub Secrets
In your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name   | Value                          |
|---------------|-------------------------------|
| `GMAIL_USER`  | your Gmail address             |
| `GMAIL_PASS`  | the 16-char App Password       |
| `ALERT_EMAIL` | where to send alerts (can be same Gmail) |

### 4. Enable Actions
Go to the **Actions** tab in your repo and click **"I understand my workflows, go ahead and enable them"**.

### 5. Test it manually
Actions tab → **Daily Job Alert** → **Run workflow** → click the green button.

Check your inbox in ~30 seconds. ✅

---

## Customise

Edit `job_alert.py` to change search terms or locations:

```python
SEARCH_QUERIES = [
    "curriculum design intern education",
    "instructional design intern education",
    "research development intern education",
]
LOCATIONS = ["India", "Remote"]
```

The cron schedule `"30 2 * * *"` = 2:30 AM UTC = **8:00 AM IST**. Change it at [crontab.guru](https://crontab.guru) if you want a different time.

---

## How it works

```
GitHub Actions (8 AM IST)
    │
    ├── Searches LinkedIn RSS, Indeed RSS, Remotive API
    ├── Filters to edu/intern roles
    ├── Deduplicates against yesterday's results
    └── Sends a clean HTML email via Gmail SMTP
```

No paid services. No APIs keys needed (except your own Gmail). Completely free.
