(function () {
  var grade = document.getElementById('id_year_level');
  var strand = document.getElementById('id_program');
  var field = document.getElementById('strand-field');

  function updateStrand() {
    var senior = grade.value === '11' || grade.value === '12';
    field.hidden = !senior;
    strand.required = senior;
    if (!senior) strand.value = '';
  }

  grade.addEventListener('change', updateStrand);
  updateStrand();
})();
