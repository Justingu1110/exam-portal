import io
import threading
from urllib.parse import urlparse
from flask import Flask, request, send_file, jsonify
from pypdf import PdfWriter, PdfReader
from playwright.sync_api import sync_playwright

app = Flask(__name__, static_folder='.', static_url_path='')

CDP_URL = 'http://localhost:9222'
REFERER = 'https://www.tcool.cc/'
ALLOWED_HOST = 'www.tcool.cc'
_lock = threading.Lock()


@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path == '':
        path = 'index.html'
    return app.send_static_file(path)


def _solve_cf(ctx, sample_url):
    """Navigate a tab to a /d/*.pdf URL so Cloudflare's Turnstile auto-solves.
    Always wait the full 5 s — checking the cookie early returns stale state
    where the cookie exists but CF still rejects new requests."""
    page = ctx.new_page()
    try:
        try:
            page.goto(sample_url, wait_until='domcontentloaded', timeout=60000)
        except Exception:
            pass
        page.wait_for_timeout(5000)
        return any(c['name'] == 'cf_clearance' for c in ctx.cookies('https://www.tcool.cc/'))
    finally:
        page.close()


def _fetch_pdfs(urls):
    """Returns {url: bytes} for whichever PDFs we managed to retrieve."""
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        try:
            cleared = any(c['name'] == 'cf_clearance' for c in ctx.cookies('https://www.tcool.cc/'))
            if not cleared:
                _solve_cf(ctx, urls[0])

            for url in urls:
                try:
                    r = ctx.request.get(url, headers={'Referer': REFERER}, timeout=30000)
                    body = r.body()
                    if r.status == 200 and body[:4] == b'%PDF':
                        results[url] = body
                        continue
                    if _solve_cf(ctx, url):
                        r = ctx.request.get(url, headers={'Referer': REFERER}, timeout=30000)
                        body = r.body()
                        if r.status == 200 and body[:4] == b'%PDF':
                            results[url] = body
                            continue
                    app.logger.warning(f'Failed {url}: HTTP {r.status} magic={body[:8]!r}')
                except Exception as e:
                    app.logger.warning(f'Failed {url}: {e}')
        finally:
            browser.close()
    return results


@app.route('/api/merge-pdf', methods=['POST', 'OPTIONS'])
def merge_pdf():
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
                'error': '無法連到本機 Chrome (CDP)。請執行 scripts/launch-chrome-cdp.sh 後再試。'
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
