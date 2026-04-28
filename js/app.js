let allExams = [];
let config = {};
let filtered = [];

async function init() {
  [config, allExams] = await Promise.all([
    fetch('data/config.json').then(r => r.json()),
    fetch('data/exams.json').then(r => r.json())
  ]);
  populateYears();
  populateCounties();
  bindEvents();
}

function populateYears() {
  const years = [...new Set(allExams.map(e => e.year))].sort((a, b) => b - a);
  const sel = document.getElementById('f-year');
  years.forEach(y => {
    const opt = document.createElement('option');
    opt.value = y;
    opt.textContent = `${y} 學年度`;
    sel.appendChild(opt);
  });
}

function populateCounties() {
  const sel = document.getElementById('f-county');
  config.counties.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    sel.appendChild(opt);
  });
}

function bindEvents() {
  document.getElementById('f-grade').addEventListener('change', updateVersionHint);
  document.getElementById('f-subject').addEventListener('change', updateVersionHint);
  document.getElementById('btn-search').addEventListener('click', doSearch);
  document.getElementById('btn-reset').addEventListener('click', resetFilters);
  document.getElementById('btn-select-all').addEventListener('click', selectAll);
  document.getElementById('btn-select-none').addEventListener('click', selectNone);
  document.getElementById('btn-open-pdfs').addEventListener('click', openSelected);
}

function updateVersionHint() {
  const grade = document.getElementById('f-grade').value;
  const subject = document.getElementById('f-subject').value;
  const hint = document.getElementById('version-hint');
  const hintText = document.getElementById('version-hint-text');

  if (grade && subject && config.defaultVersions?.[grade]?.[subject]) {
    const version = config.defaultVersions[grade][subject];
    hintText.textContent = `📖 ${grade}年級 ${subject}：我們預設使用「${version}」版`;
    hint.style.display = 'block';
  } else {
    hint.style.display = 'none';
  }
}

function getFilterValues() {
  return {
    year:      document.getElementById('f-year').value,
    grade:     document.getElementById('f-grade').value,
    semester:  document.getElementById('f-semester').value,
    examType:  document.getElementById('f-examtype').value,
    subject:   document.getElementById('f-subject').value,
    publisher: document.getElementById('f-publisher').value,
    county:    document.getElementById('f-county').value,
    answer:    document.getElementById('f-answer').value
  };
}

function doSearch() {
  const f = getFilterValues();

  filtered = allExams.filter(e => {
    if (f.year      && String(e.year)        !== f.year)      return false;
    if (f.grade     && String(e.grade)       !== f.grade)     return false;
    if (f.semester  && e.semester            !== f.semester)  return false;
    if (f.examType  && e.examType            !== f.examType)  return false;
    if (f.subject   && e.subject             !== f.subject)   return false;
    if (f.publisher && e.publisher           !== f.publisher) return false;
    if (f.county    && e.county              !== f.county)    return false;
    if (f.answer    && String(e.hasAnswerKey) !== f.answer)   return false;
    return true;
  });

  renderResults(filtered);
}

function renderResults(exams) {
  const section    = document.getElementById('results-section');
  const emptyState = document.getElementById('empty-state');
  const list       = document.getElementById('exam-list');
  const countEl    = document.getElementById('result-count');

  if (exams.length === 0) {
    section.style.display = 'none';
    emptyState.style.display = 'block';
    updateBottomBar();
    return;
  }

  emptyState.style.display = 'none';
  section.style.display = 'flex';
  countEl.textContent = `共 ${exams.length} 份考卷`;

  list.innerHTML = exams.map(e => `
    <div class="exam-card" data-id="${e.id}" onclick="onCardClick(event, this)">
      <input type="checkbox" class="exam-checkbox" data-url="${e.url}"
             onclick="event.stopPropagation(); onCardClick(event, this.closest('.exam-card'))"/>
      <div class="exam-info">
        <div class="exam-title">
          ${e.grade}年級 ${e.semester}學期 ${e.examType} ─ ${e.subject}
        </div>
        <div class="exam-meta">
          ${e.year ? `<span class="tag">${e.year} 學年</span>` : ''}
          <span class="tag publisher">${e.publisher}</span>
          ${e.county  ? `<span class="tag county">${e.county}</span>` : ''}
          ${e.school  ? `<span class="tag school">${e.school}</span>` : ''}
          <span class="tag ${e.hasAnswerKey ? 'answer' : 'no-answer'}">
            ${e.hasAnswerKey ? '含答案卷' : '無答案卷'}
          </span>
        </div>
      </div>
      <div class="btn-group" onclick="event.stopPropagation()">
        <a class="btn-pdf" href="${e.url}" target="_blank" rel="noopener">題目卷</a>
        ${e.answerUrl ? `<a class="btn-pdf btn-answer" href="${e.answerUrl}" target="_blank" rel="noopener">答案卷</a>` : ''}
      </div>
    </div>
  `).join('');

  updateBottomBar();
}

function onCardClick(event, card) {
  const cb = card.querySelector('.exam-checkbox');
  if (event.target !== cb) {
    cb.checked = !cb.checked;
  }
  card.classList.toggle('selected', cb.checked);
  updateBottomBar();
}

function selectAll() {
  document.querySelectorAll('.exam-card').forEach(card => {
    card.querySelector('.exam-checkbox').checked = true;
    card.classList.add('selected');
  });
  updateBottomBar();
}

function selectNone() {
  document.querySelectorAll('.exam-card').forEach(card => {
    card.querySelector('.exam-checkbox').checked = false;
    card.classList.remove('selected');
  });
  updateBottomBar();
}

function updateBottomBar() {
  const checked = document.querySelectorAll('.exam-checkbox:checked');
  const bar = document.getElementById('bottom-bar');
  document.getElementById('selected-count').textContent = `已選 ${checked.length} 份`;
  bar.classList.toggle('visible', checked.length > 0);
}

function openSelected() {
  const urls = [...document.querySelectorAll('.exam-checkbox:checked')]
    .map(cb => cb.dataset.url)
    .filter(Boolean);
  if (urls.length === 0) return;
  document.getElementById('popup-hint').classList.add('show');
  urls.forEach(url => window.open(url, '_blank', 'noopener'));
}

function resetFilters() {
  ['f-year','f-grade','f-semester','f-examtype','f-subject','f-publisher','f-county','f-answer']
    .forEach(id => { document.getElementById(id).value = ''; });
  document.getElementById('version-hint').style.display = 'none';
  document.getElementById('results-section').style.display = 'none';
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('popup-hint').classList.remove('show');
  updateBottomBar();
}

init();
