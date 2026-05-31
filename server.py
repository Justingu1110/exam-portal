import io
from flask import Flask, request, send_file, jsonify
import requests
from pypdf import PdfWriter, PdfReader

app = Flask(__name__, static_folder='.', static_url_path='')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.tcool.cc/',
}


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


@app.route('/api/merge-pdf', methods=['POST', 'OPTIONS'])
def merge_pdf():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json(force=True)
    urls = data.get('urls', [])

    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400

    writer = PdfWriter()
    success_count = 0

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            reader = PdfReader(io.BytesIO(resp.content))
            for page in reader.pages:
                writer.add_page(page)
            success_count += 1
        except Exception as e:
            app.logger.warning(f'Failed to fetch/merge {url}: {e}')
            continue

    if success_count == 0:
        return jsonify({'error': 'All PDFs failed to download'}), 400

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)

    return send_file(
        out,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='exams.pdf'
    )


if __name__ == '__main__':
    app.run(port=8080, debug=True)
