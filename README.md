# 小學考古題平台

A web app for browsing and downloading Taiwanese elementary school (grades 4–6) past exam PDFs. Users can filter by grade, subject, semester, exam type, publisher, and county, then open, download, or **merge into a single PDF** the matching exam files from [tcool.cc](https://www.tcool.cc).

The public site lives at <https://justingu1110.github.io/exam-portal/>.

## 兩種使用模式

| 模式 | 需要 | 能做什麼 |
|---|---|---|
| **網頁版**（GitHub Pages） | 只要瀏覽器 | 搜尋、篩選、點開或下載個別 PDF |
| **本機版**（多一個合併按鈕） | Python 3 + Chrome + 本專案 | 上述 + 一鍵把多份 PDF 合成一份 |

合併功能要繞 tcool.cc 的 Cloudflare 防護，沒辦法在 GitHub Pages 跑，必須在自己電腦起一個 Flask server，透過 Chrome DevTools Protocol (CDP) 借用本機 Chrome 的 session 抓 PDF。

---

## 合併 PDF — macOS 安裝步驟

### 一次性安裝（只做這次）

**1. 打開 Terminal**：按 `⌘ + Space` → 輸入「終端機」或「Terminal」→ Enter

**2. 確認 Python 已安裝**
```bash
python3 --version
```
應該印出 `Python 3.x.x`。若沒有，跑 `xcode-select --install` 安裝開發工具（會附 git + python3）。

**3. 下載專案**
```bash
cd ~/Desktop
git clone https://github.com/Justingu1110/exam-portal.git
cd exam-portal
```
> 第一次跑 `git` 可能會跳「需安裝開發工具」視窗，按「安裝」等幾分鐘，跑完再重來這步。

**4. 裝套件**
```bash
pip3 install -r requirements.txt
```
看到 `Successfully installed ...` 就 OK。途中若有 `WARNING ... not on PATH`，**忽略它**。

**5. 建立桌面捷徑**
```bash
bash scripts/install-desktop-shortcut.sh
```
會在你的桌面建一個 `exam-portal.command` 圖示。之後雙擊它就能啟動，不用再開 Terminal 打指令。

### 每次要用的時候

**雙擊桌面上的 `exam-portal.command`**。

會自動：
1. 跳出一個獨立 profile 的 Chrome（跟你日常用的 Chrome 完全分開）
2. 啟動 server
3. 用你預設的瀏覽器打開 <http://localhost:8080>

> 第一次雙擊若被 macOS 擋（「無法開啟，因為來自不明開發者」）：
> **右鍵點檔案 → 開啟 → 開啟**。之後雙擊就 OK。

（也可以在 Terminal 直接跑 `bash scripts/start.sh`，效果一樣。）

### 結束時

回到那個 Terminal 視窗按 `Control + C`，Chrome 跟 server 會一起關掉，然後按任意鍵關閉視窗。

### 疑難排解

| 問題 | 解法 |
|---|---|
| 按合併沒反應 / 跳「合併失敗」 | 確認 Terminal（跑著 `start.sh` 的那個）還在 |
| `Port 8080 已被佔用` 或 `Port 9222 已有東西在聽` | 上次沒關乾淨。跑 `pkill -f "scripts/start.sh"; pkill -f "python3 server.py"; pkill -f "remote-debugging-port=9222"` 再試 |
| `找不到 Chrome` | 去 <https://www.google.com/chrome/> 安裝 |
| 沒裝 Python | 跑 `xcode-select --install` |

### Windows / Linux 用戶

Chrome 啟動方式不同，其餘步驟相同：

- **Windows**：
  ```
  "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-cdp https://www.tcool.cc/
  ```
- **Linux**：
  ```bash
  google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-cdp https://www.tcool.cc/
  ```

---

## Browse-only (no setup)

If you only need search / individual download, just open <https://justingu1110.github.io/exam-portal/> — no install required. To host the static portion locally without the merge server:

```bash
python3 -m http.server 8080
```

## Architecture overview

```
exam-portal/
├── index.html                    Main search page — filter dropdowns, results, bulk open/download/merge
├── admin.html                    Admin panel — add, import, and export exam records
├── server.py                     Flask server — bridges the merge-PDF UI to a CDP-attached Chrome
├── css/
│   └── main.css                  All styles (shared between index and admin)
├── js/
│   ├── app.js                    Front-end logic: filter, search, render, PDF modal, merge
│   └── admin.js                  Admin logic: CRUD on the in-memory exam list, JSON import/export
├── data/
│   ├── exams.json                Exam database — array of exam records
│   └── config.json               App config — grade/subject/publisher lists, default-publisher map
└── scripts/
    ├── fetch_exams.py            Scraper that crawls tcool.cc and regenerates exams.json
    ├── launch-chrome-cdp.sh         Launches just the isolated Chrome (used by start.sh)
    ├── start.sh                     One-shot: launches Chrome + server, Ctrl+C tears both down
    └── install-desktop-shortcut.sh  Creates a double-clickable launcher on ~/Desktop (macOS)
```

### Data flow

1. On page load, `app.js` fetches `data/config.json` and `data/exams.json`.
2. Filter dropdowns dynamically disable options that have no matching records.
3. Search results render as cards; selected cards can be opened in new tabs, downloaded individually, or merged into a single PDF.
4. Merge calls `POST /api/merge-pdf` on `server.py`. The server connects to the user's CDP Chrome on `localhost:9222`, runs `fetch()` for each PDF inside a tcool.cc page (so Cloudflare sees a real browser); on a 403 it navigates the page to that URL to let Cloudflare's JS challenge auto-solve, then retries. The collected PDFs are merged with `pypdf` and returned as one file.
5. `admin.html` lets you add exam entries manually, or import/export the full `exams.json` — push the updated file to update the live data for all users.
6. To bulk-refresh the dataset, run `scripts/fetch_exams.py` and commit the updated `data/exams.json`.
