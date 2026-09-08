/* Pure grading/CSV functions are shared by the offline page and Node tests. */
'use strict';
const GraderV3 = (() => {
  const fields = ['pass_A','critical_A','credential_violation_A','pass_B','critical_B','credential_violation_B','preferred','notes'];
  const blank = () => Object.fromEntries(fields.map(k => [k, '']));
  function validate(v, partial = true) {
    for (const k of fields) if (typeof v[k] !== 'string') throw Error(`Missing or invalid ${k}`);
    for (const k of fields.slice(0, 6)) if (!['true','false', ...(partial ? [''] : [])].includes(v[k])) throw Error(`Choose Yes/No or PASS/FAIL for ${k}`);
    if (!['A','B','tie', ...(partial ? [''] : [])].includes(v.preferred)) throw Error('Choose A, B or Tie');
    for (const side of ['A','B']) {
      if (v[`pass_${side}`] === 'true' && (v[`critical_${side}`] === 'true' || v[`credential_violation_${side}`] === 'true')) throw Error(`${side}: a critical or credential violation cannot PASS`);
      if (v[`credential_violation_${side}`] === 'true' && v[`critical_${side}`] === 'false') throw Error(`${side}: credential/verification violations are critical`);
    }
    if (!partial && !v.notes.trim()) throw Error('An evidence note is required');
    return v;
  }
  function complete(v) { try { validate(v, false); return true; } catch { return false; } }
  function change(v, field, value) {
    if (!fields.includes(field)) throw Error('Unknown grading field');
    return validate({...v, [field]: value});
  }
  function parseCSV(text) {
    text = text.replace(/^\uFEFF/, '');
    const result = []; let row = [], value = '', state = 'start', active = false;
    const cell = () => { row.push(value); value = ''; state = 'start'; };
    const record = () => { cell(); result.push(row); row = []; active = false; };
    for (let i = 0; i < text.length; i++) {
      const c = text[i]; active = true;
      if (state === 'quoted') {
        if (c === '"') { if (text[i+1] === '"') { value += '"'; i++; } else state = 'closed'; }
        else value += c;
      } else if (c === ',') cell();
      else if (c === '\r' || c === '\n') { if (c === '\r' && text[i+1] === '\n') i++; record(); }
      else if (c === '"' && state === 'start') state = 'quoted';
      else { if (state === 'closed' || c === '"') throw Error('Malformed CSV quoting'); value += c; state = 'plain'; }
    }
    if (state === 'quoted') throw Error('Unclosed CSV quote');
    if (active || row.length || value) record();
    return result;
  }
  function restore(text, data) {
    const [header, ...records] = parseCSV(text);
    if (JSON.stringify(header) !== JSON.stringify(data.columns)) throw Error('Wrong columns: use this v3 grader’s CSV, not the older 54-pair sheet');
    if (records.length !== data.rows.length) throw Error(`Expected all ${data.rows.length} pairs, including incomplete ones`);
    const expected = new Map(data.rows.map(r => [r.item_id, r]));
    const marks = Object.create(null);
    for (const cells of records) {
      if (cells.length !== header.length) throw Error('Wrong CSV cell count');
      const r = Object.fromEntries(header.map((k,i) => [k,cells[i]]));
      const original = expected.get(r.item_id);
      if (!original || Object.hasOwn(marks, r.item_id)) throw Error('Unknown or duplicate item ID');
      if (data.immutable.some(k => r[k] !== original[k])) throw Error(`${r.item_id}: question, rubric or A/B answer differs from the frozen sheet`);
      marks[r.item_id] = validate(Object.fromEntries(fields.map(k => [k,r[k]])));
    }
    return marks;
  }
  function csv(data, marks, final = false) {
    const quote = s => '"' + s.replace(/"/g, '""') + '"';
    const records = data.rows.map(r => {
      const v = validate(marks[r.item_id] || blank(), !final);
      // Only user notes need formula protection; immutable CSV cells are already escaped.
      const notes = /^[\t\r\n]/.test(v.notes) || /^[\s]*[=+@-]/.test(v.notes) ? "'" + v.notes : v.notes;
      return data.columns.map(k => quote(data.immutable.includes(k) ? r[k] : k === 'notes' ? notes : v[k])).join(',');
    });
    return [data.columns.map(quote).join(','), ...records].join('\r\n') + '\r\n';
  }
  function keyboardAction(e) {
    if (e.defaultPrevented || e.isComposing || e.ctrlKey || e.metaKey || e.shiftKey ||
        /^(INPUT|TEXTAREA|SELECT)$/.test(e.target?.tagName) || e.target?.isContentEditable) return null;
    if (e.key === 'ArrowRight') return 'next';
    if (e.key === 'ArrowLeft') return 'previous';
    if (e.altKey && e.key.toLowerCase() === 'n') return 'incomplete';
    return null;
  }
  return {fields, blank, validate, complete, change, parseCSV, restore, csv, keyboardAction};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = GraderV3;
if (typeof document !== 'undefined') (() => {
  const data = JSON.parse(document.getElementById('grading-data').textContent);
  const G = GraderV3, $ = id => document.getElementById(id);
  const store = `ghl-v3-final01-grades-${data.source_sha256}`;
  let marks = Object.create(null), current = data.rows[0].item_id, importing = false;
  const value = id => marks[id] || G.blank();
  const status = s => { $('status').textContent = s; };
  try {
    const saved = localStorage.getItem(store);
    if (saved) { marks = G.restore(saved, data); status('Restored saved v3 progress from this browser. Export a CSV backup regularly.'); }
  } catch (e) { status(`Saved progress was not loaded: ${e.message}. Export any recoverable backup before resetting.`); }
  function save() {
    try { localStorage.setItem(store, G.csv(data, marks)); status('Saved in this browser. Export a progress CSV for a durable backup.'); }
    catch (e) { status(`Browser save failed: ${e.message}. Export your progress CSV now.`); }
  }
  function visible() {
    const q = $('search').value.toLowerCase(), f = $('filter').value;
    return data.rows.filter(r => (`${r.item_id} ${r.query}`).toLowerCase().includes(q) && (f === 'all' || f === 'incomplete' && !G.complete(value(r.item_id)) || f === 'critical' && ['A','B'].some(s => value(r.item_id)[`critical_${s}`] === 'true')));
  }
  function button(label, handler) { const b = document.createElement('button'); b.type = 'button'; b.textContent = label; b.onclick = handler; return b; }
  function mark(field, selected) {
    try { marks[current] = G.change(value(current), field, selected); save(); refresh(); }
    catch (e) { status(`${e.message}. Clear or change the conflicting mark first; no grades were changed.`); }
  }
  function choices(container, field, options) {
    for (const [val,label] of options) {
      const b = button(label, () => mark(field, value(current)[field] === val ? '' : val));
      b.dataset.field = field; b.dataset.value = val; container.append(b);
    }
  }
  function refresh() {
    const done = data.rows.filter(r => G.complete(value(r.item_id))).length;
    $('progressText').textContent = `${done} / ${data.rows.length} complete`; $('progress').value = done;
    $('exportFinal').disabled = done !== data.rows.length;
    $('completion').textContent = G.complete(value(current)) ? 'This pair is complete. You can still revise it before unblinding.' : 'Incomplete: record all six answer judgments, preference and evidence note.';
    document.querySelectorAll('[data-field]').forEach(b => b.setAttribute('aria-pressed', String(value(current)[b.dataset.field] === b.dataset.value)));
    $('index').replaceChildren(); $('jump').replaceChildren();
    for (const r of visible()) {
      const n = data.rows.indexOf(r)+1, v = value(r.item_id);
      const b = button(String(n), () => show(r.item_id));
      b.classList.toggle('done', G.complete(v)); b.classList.toggle('flagged', v.critical_A === 'true' || v.critical_B === 'true'); b.classList.toggle('current', r.item_id === current);
      b.setAttribute('aria-label', `Question ${n}${G.complete(v) ? ', complete' : ', incomplete'}`);
      if (r.item_id === current) b.setAttribute('aria-current', 'true'); $('index').append(b);
      const o = document.createElement('option'); o.value = r.item_id; o.textContent = `${n}. ${r.item_id}${G.complete(v) ? ' — complete' : ''}`; $('jump').append(o);
    }
    $('jump').value = current;
  }
  function show(id) {
    current = id; const r = data.rows.find(r => r.item_id === id);
    $('pair').classList.toggle('hidden', !r); $('empty').classList.toggle('hidden', !!r);
    if (!r) { refresh(); return; }
    $('itemLabel').textContent = `Pair ${data.rows.indexOf(r)+1} of ${data.rows.length} · ${r.item_id}`;
    $('query').textContent = r.query; $('acceptable').textContent = r.acceptable_actions; $('prohibited').textContent = r.critical_fail_if;
    $('answers').replaceChildren();
    for (const side of ['A','B']) {
      const card = document.createElement('article'); card.className = 'side';
      const h = document.createElement('h2'); h.className = 'sidehead'; h.textContent = `Answer ${side}`;
      const answer = document.createElement('div'); answer.className = 'text answer'; answer.textContent = r[`answer_${side}`]; card.append(h,answer);
      for (const [field,label,opts] of [
        [`pass_${side}`,`Answer ${side}: task success`,[['true','PASS'],['false','FAIL']]],
        [`critical_${side}`,`Answer ${side}: critical failure?`,[['false','No'],['true','Yes']]],
        [`credential_violation_${side}`,`Answer ${side}: credential/verification violation?`,[['false','No'],['true','Yes']]]
      ]) {
        const fs = document.createElement('fieldset'), legend = document.createElement('legend'), group = document.createElement('div');
        legend.textContent = label; group.className = 'choices'; choices(group,field,opts); fs.append(legend,group); card.append(fs);
      }
      $('answers').append(card);
    }
    $('notes').value = value(current).notes; refresh();
  }
  function navigate(delta) { const list = visible(); if (!list.length) return; const i = list.findIndex(r => r.item_id === current); show(list[(Math.max(i,0)+delta+list.length)%list.length].item_id); }
  function nextIncomplete() {
    const start = data.rows.findIndex(r => r.item_id === current);
    for (let step = 1; step <= data.rows.length; step++) { const r = data.rows[(start+step+data.rows.length)%data.rows.length]; if (!G.complete(value(r.item_id))) { $('filter').value = 'all'; $('search').value = ''; show(r.item_id); return; } }
    status('All pairs are complete. Export your completed CSV before unblinding.');
  }
  function download(final) {
    try {
      const blob = new Blob([G.csv(data,marks,final)], {type:'text/csv;charset=utf-8'}), url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `v3-blind-grading-${final ? 'scored' : 'progress'}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      status('CSV download requested. Keep this export as a record; this page does not submit or unblind it.');
    } catch (e) { status(e.message); }
  }
  for (const [id,rules] of [['passRules',data.pass_criteria],['criticalRules',data.critical_failure]]) for (const rule of rules) { const li = document.createElement('li'); li.textContent = rule; $(id).append(li); }
  choices($('preference'),'preferred',[['A','Prefer A'],['B','Prefer B'],['tie','Tie']]);
  $('notes').oninput = () => { if (!current) return; marks[current] = G.change(value(current),'notes',$('notes').value); save(); refresh(); };
  $('previous').onclick = () => navigate(-1); $('next').onclick = () => navigate(1); $('nextUnscored').onclick = nextIncomplete;
  $('jump').onchange = () => show($('jump').value);
  for (const id of ['filter','search']) $(id).addEventListener('input', () => { const list = visible(); show(list.some(r => r.item_id === current) ? current : list[0]?.item_id || ''); });
  $('exportFinal').onclick = () => download(true); $('exportProgress').onclick = () => download(false);
  $('restore').onclick = () => $('importFile').click();
  $('importFile').onchange = async () => {
    const file = $('importFile').files[0]; if (!file || importing) return;
    importing = true;
    try {
      const restored = G.restore(await file.text(),data);
      if (!confirm('Replace this browser’s v3 marks with this CSV? Export current progress first if you want to keep it.')) return;
      marks = restored; save(); show(current || data.rows[0].item_id);
    } catch (e) { status(`Import rejected; current marks are unchanged. ${e.message}`); }
    finally { importing = false; $('importFile').value = ''; }
  };
  $('reset').onclick = () => {
    if (!confirm('Clear only this v3 grader’s marks in this browser? Export a progress CSV first; clearing cannot be undone here. Older grader marks and downloaded files are untouched.')) return;
    marks = Object.create(null); save(); show(current || data.rows[0].item_id);
  };
  document.addEventListener('keydown', e => {
    const action = G.keyboardAction(e);
    if (!action) return;
    e.preventDefault();
    if (action === 'next') navigate(1);
    else if (action === 'previous') navigate(-1);
    else nextIncomplete();
  });
  show(current);
})();
