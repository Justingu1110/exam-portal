# 小學考古題平台

A static web app for browsing and downloading Taiwanese elementary school (grades 4–6) past exam PDFs. Users can filter by grade, subject, semester, exam type, publisher, and county, then open or download the matching PDF files directly from [tcool.cc](https://www.tcool.cc).

## How to run locally

The app uses `fetch()` to load JSON data files, so it must be served over HTTP (opening `index.html` directly via `file://` will fail due to browser CORS restrictions).

**Option 1 — Python (no dependencies)**

```bash
python3 -m http.server 8080
```

Then open <http://localhost:8080> in your browser.

**Option 2 — Node.js**

```bash
npx serve .
```

Then open the URL printed in the terminal (usually <http://localhost:3000>).

**Option 3 — VS Code**

Install the [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) extension, right-click `index.html`, and choose **Open with Live Server**.

> No build step or package installation is required — the project is plain HTML, CSS, and JavaScript.

## Architecture overview

```
exam-portal/
├── index.html          Main search page — filter dropdowns, results grid, bulk open/download
├── admin.html          Admin panel — add, import, and export exam records
├── css/
│   └── main.css        All styles (shared between index and admin)
├── js/
│   ├── app.js          Front-end logic: filter, search, render, PDF modal
│   └── admin.js        Admin logic: CRUD on the in-memory exam list, JSON import/export
├── data/
│   ├── exams.json      Exam database — array of exam records (school, grade, subject, PDF URLs, …)
│   └── config.json     App config — grade/subject/publisher lists, per-grade default publisher map
└── scripts/
    └── fetch_exams.py  One-off Python scraper that crawls tcool.cc and regenerates exams.json
```

### Data flow

1. On page load, `app.js` fetches `data/config.json` and `data/exams.json`.
2. Filter dropdowns dynamically disable options that have no matching records.
3. Search results render as cards; selected cards can be opened in new tabs or downloaded via a modal.
4. `admin.html` lets you add exam entries manually, or import/export the full `exams.json` — push the updated file to update the live data for all users.
5. To bulk-refresh the dataset, run `scripts/fetch_exams.py` (Python 3, stdlib only) and commit the updated `data/exams.json`.
