document.addEventListener('DOMContentLoaded', function() {
    const dateSelector = document.getElementById('dateSelector');
    const mensaSelector = document.getElementById('mensaSelector');
    const submitButton = document.getElementById('submitButton');

    submitButton.addEventListener('click', function() {
        const selectedDate = dateSelector.value;
        const selectedMensa = mensaSelector.value;
        window.location.href = `/mensa/${selectedMensa}?date=${selectedDate}`;
    });
});