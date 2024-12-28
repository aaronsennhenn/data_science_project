document.addEventListener('DOMContentLoaded', function () {
    const submitRatingButtons = document.querySelectorAll('.submit-rating');
    const mensaDropdown = document.getElementById('mensa-dropdown');

    submitRatingButtons.forEach(button => {
        button.addEventListener('click', function () {
            const menuLine = this.getAttribute('data-menu-line');
            const id = this.getAttribute('data-id');
            const rating = document.querySelector(`input[name="rating_${menuLine}"]:checked`).value;

            if (rating) {
                const feedback = this.nextElementSibling;
                feedback.classList.remove('hidden');
                feedback.textContent = 'Rating received!';
                
                setTimeout(() => {
                    feedback.classList.add('hidden');
                }, 3000);
            } else {
                alert('Please select a rating before submitting.');
            }

            const formData = new FormData();
            formData.append('id', id);
            formData.append('rating', rating);

            fetch('/menu', {
                method: 'POST',
                body: formData,
            })
        });
    });

    // Handle mensa selection
    mensaDropdown.addEventListener('change', function() {
        const form = document.getElementById('filter-form');
        if (this.value === 'all') {
            // Submit form to refresh with all mensa results
            form.submit();
        }
    });

    // Handle omnivore checkbox
    const omnivoreCheckbox = document.getElementById('diet_omnivore');
    const otherCheckboxes = document.querySelectorAll('input[name="selected_diet_meat"]:not(#diet_omnivore)');

    omnivoreCheckbox.addEventListener('change', function() {
        if (this.checked) {
            otherCheckboxes.forEach(cb => {
                cb.checked = false;
                cb.disabled = true;
            });
        } else {
            otherCheckboxes.forEach(cb => {
                cb.disabled = false;
            });
        }
    });
});