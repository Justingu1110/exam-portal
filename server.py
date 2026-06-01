import base64
import io
import threading
from urllib.parse import urlparse
from flask import Flask, request, send_file, jsonify
from pypdf import PdfWriter, PdfReader
from playwright.sync_api import sync_playwright

app = Flask(__name__, static_folder='.', static_url_path='')

CDP_URL = 'http://localhost:9222'
ALLOWED_HOST = 'www.tcool.cc'
HOMEPAGE = f'https://{ALLOWED_HOST}/'
_lock = threading.Lock()

# Fetch via the browser's own network stack so Cloudflare sees a real Chrome
# request (Playwright's APIRequestContext fails the bot check even with cookies).
_BROWSER_FETCH_JS = """
async (url) => {
  const r = await fetch(url, {credentials: 'include'});
  if (!r.ok) return {ok: false, status: r.status};
  const buf = await r.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let bin = '';
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return {ok: true, status: r.status, b64: btoa(bin)};
}
"""


@app.after_request
def add_cors(response):
    """Attach permissive CORS headers to every response for local dev use."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from the repo root; fall back to index.html for /."""
    if path == '':
        path = 'index.html'
    return app.send_static_file(path)


def _try_fetch(page, url):
    """Fetch url via the CDP page's browser fetch(); return PDF bytes or None.

    Runs _BROWSER_FETCH_JS inside the live page so the request carries the
    page's cookies and origin, bypassing Cloudflare's bot checks.  Validates
    the response body starts with the %PDF magic bytes before returning it;
    returns None on any network error or if the body is not a valid PDF.
    """
    try:
        res = page.evaluate(_BROWSER_FETCH_JS, url)
        if res.get('ok'):
            body = base64.b64decode(res['b64'])
            if body[:4] == b'%PDF':
                return body
    except Exception as e:
        app.logger.warning(f'evaluate err {url}: {e}')
    return None


def _fetch_pdfs(urls):
    """Returns {url: bytes} for whichever PDFs we managed to retrieve.
    Runs fetch() inside a tcool.cc page so Cloudflare sees a real browser.
    Cloudflare challenges per-URL, so on a 403 we navigate to the URL once
    (which triggers CF's JS auto-solve in a real browser) and then retry."""
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        try:
            page = ctx.new_page()
            try:
                page.goto(HOMEPAGE, wait_until='domcontentloaded', timeout=30000)
            except Exception as e:
                app.logger.warning(f'homepage navigate failed: {e}')

            for url in urls:
                body = _try_fetch(page, url)
                if body is None:
                    try:
                        page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    except Exception:
                        pass
                    page.wait_for_timeout(4000)
                    body = _try_fetch(page, url)
                if body:
                    results[url] = body
                else:
                    app.logger.warning(f'Failed {url}: CF challenge could not be cleared')
            page.close()
        finally:
            browser.close()
    return results


@app.route('/api/merge-pdf', methods=['POST', 'OPTIONS'])
def merge_pdf():
    """POST /api/merge-pdf — download and merge a list of PDF URLs into one file.

    Expects JSON body: {"urls": ["https://...", ...]}.
    All URLs must be https://www.tcool.cc/...pdf (validated before fetching).
    A threading lock serialises requests because CDP operates on a single page.
    Returns the merged PDF as a downloadable attachment, or a JSON error on
    failure (400 for bad input, 503 if the local Chrome CDP is unreachable).
    """
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json(force=True)
    urls = data.get('urls', [])
    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400

    for u in urls:
        parsed = urlparse(u)
        if parsed.scheme != 'https' or parsed.hostname != ALLOWED_HOST or not parsed.path.endswith('.pdf'):
            return jsonify({'error': f'URL not allowed: {u}'}), 400

    with _lock:
        try:
            pdfs = _fetch_pdfs(urls)
        except Exception as e:
            app.logger.error(f'CDP connect failed: {e}')
            return jsonify({
                'error': '無法連到本機 Chrome (CDP)。請執行 scripts/start.sh 後再試。'
            }), 503

    if not pdfs:
        return jsonify({'error': 'All PDFs failed to download'}), 400

    writer = PdfWriter()
    for url in urls:
        body = pdfs.get(url)
        if not body:
            continue
        try:
            for page in PdfReader(io.BytesIO(body)).pages:
                writer.add_page(page)
        except Exception as e:
            app.logger.warning(f'merge err {url}: {e}')

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return send_file(out, mimetype='application/pdf', as_attachment=True, download_name='exams.pdf')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
