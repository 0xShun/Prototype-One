(function () {
  var bar = document.querySelector('[data-filter-bar]');
  if (!bar) return;
  var scope = bar.closest('.support-page');
  var rows = scope.querySelectorAll('tbody tr');
  var empty = scope.querySelector('.filter-empty');
  var controls = bar.querySelectorAll('[data-filter]');

  function apply() {
    var active = {};
    controls.forEach(function (c) { active[c.dataset.filter] = c.value.trim().toLowerCase(); });
    var shown = 0;
    rows.forEach(function (row) {
      var section = row.closest('[data-section]');
      var ok = row.textContent.toLowerCase().indexOf(active.search || '') !== -1;
      if (ok && active.section && section) ok = section.dataset.section === active.section;
      Object.keys(active).forEach(function (key) {
        if (!ok || !active[key] || key === 'search' || key === 'section') return;
        ok = (row.dataset[key] || '').toLowerCase() === active[key];
      });
      row.hidden = !ok;
      if (ok) shown++;
    });
    scope.querySelectorAll('[data-section]').forEach(function (section) {
      var sectionRows = section.querySelectorAll('tbody tr');
      var anyVisible = !sectionRows.length || Array.prototype.some.call(sectionRows, function (r) { return !r.hidden; });
      var filtering = Object.keys(active).some(function (k) { return active[k]; });
      section.hidden = filtering && !anyVisible;
    });
    if (empty) empty.hidden = shown > 0 || !rows.length;
  }

  bar.addEventListener('input', apply);
  bar.addEventListener('change', apply);
  bar.querySelector('[data-filter-reset]').addEventListener('click', function () {
    controls.forEach(function (c) { c.value = ''; });
    apply();
  });
})();
