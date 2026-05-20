import os
import json
import hashlib
import smtplib
import urllib.request
import urllib.parse
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── CONFIG ────────────────────────────────────────────────────────────────────
SEARCH_QUERIES = [
    "curriculum design intern education",
    "instructional design intern education",
    "research development intern education",
]
LOCATIONS = ["India", "Remote"]

GMAIL_USER   = os.environ["GMAIL_USER"]    # your Gmail address
GMAIL_PASS   = os.environ["GMAIL_PASS"]    # Gmail App Password
ALERT_EMAIL  = os.environ["ALERT_EMAIL"]   # where to send alerts (can be same)

SEEN_FILE = "seen_jobs.json"               # tracks already-sent jobs
# ─────────────────────────────────────────────────────────────────────────────


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def job_id(job: dict) -> str:
    key = f"{job['title']}|{job['company']}|{job['location']}"
    return hashlib.md5(key.encode()).hexdigest()


def search_remotive(keyword: str) -> list[dict]:
    """Search Remotive (remote jobs, free API)."""
    url = "https://remotive.com/api/remote-jobs?search=" + urllib.parse.quote(keyword) + "&limit=20"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        jobs = []
        for j in data.get("jobs", []):
            title = j.get("title", "")
            # filter to intern / education related
            title_l = title.lower()
            if not any(k in title_l for k in ["intern", "curriculum", "instructional", "research", "education", "learning", "training", "e-learning"]):
                continue
            jobs.append({
                "title":    title,
                "company":  j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Remote"),
                "url":      j.get("url", ""),
                "source":   "Remotive",
                "posted":   j.get("publication_date", "")[:10],
            })
        return jobs
    except Exception as e:
        print(f"Remotive error: {e}")
        return []


def search_linkedin_rss(keyword: str, location: str) -> list[dict]:
    """LinkedIn public RSS feed (no auth needed)."""
    q   = urllib.parse.quote(keyword)
    loc = urllib.parse.quote(location)
    url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}&f_E=1&f_JT=I&sortBy=DD"
    # LinkedIn RSS endpoint
    rss_url = f"https://www.linkedin.com/jobs/search.rss?keywords={q}&location={loc}&f_JT=I&sortBy=DD"
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read().decode("utf-8", errors="ignore")
        import re
        items = re.findall(r"<item>(.*?)</item>", text, re.DOTALL)
        jobs = []
        for item in items[:10]:
            title   = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item)
            link    = re.search(r"<link>(.*?)</link>", item)
            company = re.search(r"<source.*?>(.*?)</source>", item)
            if not title:
                continue
            jobs.append({
                "title":    title.group(1).strip(),
                "company":  company.group(1).strip() if company else "",
                "location": location,
                "url":      link.group(1).strip() if link else url,
                "source":   "LinkedIn",
                "posted":   str(date.today()),
            })
        return jobs
    except Exception as e:
        print(f"LinkedIn RSS error ({keyword}, {location}): {e}")
        return []


def search_indeed_rss(keyword: str, location: str) -> list[dict]:
    """Indeed RSS feed (no auth needed)."""
    q   = urllib.parse.quote(keyword)
    loc = urllib.parse.quote(location)
    rss_url = f"https://in.indeed.com/rss?q={q}&l={loc}&jt=internship&sort=date"
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read().decode("utf-8", errors="ignore")
        import re
        items = re.findall(r"<item>(.*?)</item>", text, re.DOTALL)
        jobs = []
        for item in items[:10]:
            title   = re.search(r"<title>(.*?)</title>", item)
            link    = re.search(r"<link>(.*?)</link>", item)
            company = re.search(r"<source.*?>(.*?)</source>", item)
            if not title:
                continue
            t = title.group(1).replace("&amp;", "&").replace("&#39;", "'").strip()
            jobs.append({
                "title":    t,
                "company":  company.group(1).strip() if company else "",
                "location": location,
                "url":      link.group(1).strip() if link else "",
                "source":   "Indeed",
                "posted":   str(date.today()),
            })
        return jobs
    except Exception as e:
        print(f"Indeed RSS error ({keyword}, {location}): {e}")
        return []


def fetch_all_jobs() -> list[dict]:
    jobs = []
    for query in SEARCH_QUERIES:
        jobs += search_remotive(query)
        for loc in LOCATIONS:
            jobs += search_linkedin_rss(query, loc)
            jobs += search_indeed_rss(query, loc)
    # deduplicate by id
    seen_ids, unique = set(), []
    for j in jobs:
        jid = job_id(j)
        if jid not in seen_ids:
            seen_ids.add(jid)
            j["_id"] = jid
            unique.append(j)
    return unique


def build_email_html(new_jobs: list[dict]) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    rows = ""
    for j in new_jobs:
        source_color = {
            "LinkedIn": "#0077B5",
            "Indeed":   "#2164F3",
            "Remotive": "#00A86B",
        }.get(j["source"], "#666")

        rows += f"""
        <tr style="border-bottom:1px solid #f0f0f0;">
          <td style="padding:16px 12px;">
            <a href="{j['url']}" style="font-size:15px;font-weight:600;color:#1a1a1a;text-decoration:none;">{j['title']}</a><br>
            <span style="font-size:13px;color:#555;">{j['company']}</span>
          </td>
          <td style="padding:16px 12px;font-size:13px;color:#555;">{j['location']}</td>
          <td style="padding:16px 12px;">
            <span style="background:{source_color};color:#fff;font-size:11px;padding:3px 8px;border-radius:4px;">{j['source']}</span>
          </td>
          <td style="padding:16px 12px;">
            <a href="{j['url']}" style="background:#1a1a1a;color:#fff;font-size:12px;padding:6px 14px;border-radius:6px;text-decoration:none;">Apply →</a>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:680px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

  <div style="background:#1a1a1a;padding:28px 32px;">
    <p style="margin:0;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:1px;">Daily Job Alert</p>
    <h1 style="margin:6px 0 0;font-size:24px;color:#fff;">📚 Education Internships</h1>
    <p style="margin:8px 0 0;font-size:13px;color:#aaa;">{today} &nbsp;·&nbsp; {len(new_jobs)} new listing{'s' if len(new_jobs)!=1 else ''}</p>
  </div>

  <div style="padding:24px 32px;">
    <p style="margin:0 0 20px;font-size:14px;color:#555;">
      Searching for: <strong>Curriculum Design · Instructional Design · R&D</strong> internships in <strong>India &amp; Remote</strong>
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #eee;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#f9f9f9;">
          <th style="padding:12px;text-align:left;font-size:12px;color:#888;font-weight:500;text-transform:uppercase;">Role</th>
          <th style="padding:12px;text-align:left;font-size:12px;color:#888;font-weight:500;text-transform:uppercase;">Location</th>
          <th style="padding:12px;text-align:left;font-size:12px;color:#888;font-weight:500;text-transform:uppercase;">Source</th>
          <th style="padding:12px;text-align:left;font-size:12px;color:#888;font-weight:500;text-transform:uppercase;"></th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <div style="padding:20px 32px;border-top:1px solid #f0f0f0;text-align:center;">
    <p style="margin:0;font-size:12px;color:#bbb;">Sent automatically every morning · Sources: LinkedIn, Indeed, Remotive</p>
  </div>
</div>
</body></html>"""


def send_email(jobs: list[dict]):
    html = build_email_html(jobs)
    today = datetime.now().strftime("%b %d")
    subject = f"📚 {len(jobs)} new education intern job{'s' if len(jobs)!=1 else ''} – {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = ALERT_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_PASS)
        s.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())
    print(f"✅ Sent alert with {len(jobs)} jobs to {ALERT_EMAIL}")


def main():
    print("Fetching jobs...")
    all_jobs = fetch_all_jobs()
    seen     = load_seen()

    new_jobs = [j for j in all_jobs if j["_id"] not in seen]
    print(f"Found {len(all_jobs)} total, {len(new_jobs)} new")

    if new_jobs:
        send_email(new_jobs)
        seen.update(j["_id"] for j in new_jobs)
        save_seen(seen)
    else:
        print("No new jobs today — no email sent.")


if __name__ == "__main__":
    main()
