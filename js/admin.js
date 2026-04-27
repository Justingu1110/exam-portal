let exams = [];
let config = {};

async function init() {
  config = await fetch('data/config.json').then(r => r.json());
  exams  = await fetch('data/exams.json').then(r => r.json());
  populateCounties();
  renderTable();
  bindEvents();
}

function populateCounties() {
  const sel = document.getElementById('a-county');
  config.counties.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    sel.appendChild(opt);
  });
}

function bindEvents() {
  document.getElementById('btn-add').addEventListener('click', addExam);
  document.getElementById('btn-export').addEventListener('click', exportJSON);
  document.getElementById('file-import').addEventListener('change', importJSON);
}

function showAlert(msg, type) {
  const el = document.getElementById('alert');
  el.textContent = msg;
  el.className = `alert ${type}`;
  setTimeout(() => { el.className = 'alert'; }, 3000);
}

function addExam() {
  const year      = document.getElementById('a-year').value.trim();
  const grade     = document.getElementById('a-grade').value;
  const semester  = document.getElementById('a-semester').value;
  const examType  = document.getElementById('a-examtype').value;
  const subject   = document.getElementById('a-subject').value;
  const publisher = document.getElementById('a-publisher').value;
  const county    = document.getElementById('a-county').value;
  const school    = document.getElementById('a-school').value.trim();
  const hasAnswer = document.getElementById('a-answer').value === 'true';
  const url       = document.getElementById('a-url').value.trim();

  if (!grade || !semester || !examType || !subject || !publisher || !url) {
    showAlert('請填寫所有必填欄位（年級、學期、段考、科目、出版社、PDF 網址）', 'error');
    return;
  }
  if (!url.startsWith('http')) {
    showAlert('PDF 網址格式不正確，請貼上完整網址', 'error');
    return;
  }

  const newExam = {
    id: String(Date.now()),
    year: parseInt(year),
    grade,
    semester,
    examType,
    subject,
    publisher,
    county,
    school,
    hasAnswerKey: hasAnswer,
    url
  };

  exams.push(newExam);
  renderTable();
  clearForm();
  showAlert('✓ 新增成功！記得匯出 JSON 並更新到 GitHub', 'success');
}

function clearForm() {
  ['a-year','a-school','a-url'].forEach(id => { document.getElementById(id).value = ''; });
  ['a-grade','a-semester','a-examtype','a-subject','a-publisher','a-county'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('a-answer').value = 'true';
}

function deleteExam(id) {
  if (!confirm('確定要刪除這筆資料嗎？')) return;
  exams = exams.filter(e => e.id !== id);
  renderTable();
  showAlert('已刪除，記得匯出 JSON 更新到 GitHub', 'success');
}

function renderTable() {
  const tbody = document.getElementById('exam-tbody');
  document.getElementById('total-count').textContent = exams.length;

  if (exams.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:24px;color:var(--gray-400)">尚無考卷，請新增</td></tr>';
    return;
  }

  tbody.innerHTML = exams.map(e => `
    <tr>
      <td>${e.year}</td>
      <td>${e.grade}年</td>
      <td>${e.semester}</td>
      <td>${e.examType}</td>
      <td>${e.subject}</td>
      <td>${e.publisher}</td>
      <td>${e.county || '—'}</td>
      <td>${e.school || '—'}</td>
      <td>${e.hasAnswerKey ? '✓' : '✗'}</td>
      <td><button class="btn-delete" onclick="deleteExam('${e.id}')">刪除</button></td>
    </tr>
  `).join('');
}

function exportJSON() {
  const blob = new Blob([JSON.stringify(exams, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'exams.json';
  a.click();
  URL.revokeObjectURL(a.href);
  showAlert('✓ exams.json 已下載，請放到 data/ 資料夾並推上 GitHub', 'success');
}

function importJSON(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    try {
      const imported = JSON.parse(ev.target.result);
      if (!Array.isArray(imported)) throw new Error('格式錯誤');
      exams = imported;
      renderTable();
      showAlert(`✓ 匯入成功，共 ${exams.length} 筆`, 'success');
    } catch {
      showAlert('匯入失敗：JSON 格式不正確', 'error');
    }
  };
  reader.readAsText(file);
  e.target.value = '';
}

init();
