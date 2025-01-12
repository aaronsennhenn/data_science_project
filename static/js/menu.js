document.addEventListener('DOMContentLoaded', function () {
    const submitRatingButtons = document.querySelectorAll('.submit-rating');
    const mensaDropdown = document.getElementById('mensa-dropdown');
    const expandButtons = document.querySelectorAll('.expand-button');

    expandButtons.forEach(button => {
        button.addEventListener('click', function () {
            const content = this.previousElementSibling;
            const isExpanded = content.classList.contains('expanded');
            
            if (isExpanded) {
                content.style.height = '8rem';
                content.classList.remove('expanded');
                this.textContent = this.getAttribute('data-expand-text');
            } else {
                content.style.height = content.scrollHeight + 'px';
                content.classList.add('expanded');
                this.textContent = this.getAttribute('data-collapse-text');
            }
        });
    });
    
    submitRatingButtons.forEach(button => {
        button.addEventListener('click', function () {
            const id = this.getAttribute('data-id');
            const rating = document.querySelector(`input[name="rating_${id}"]:checked`).value;
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

// function for rate more dishes popup
function togglePopup() {
    document.getElementById("popup-1").classList.toggle("active");
}
function toggleDescriptionPopup(dishId) {
    document.getElementById("description-popup-" + dishId).classList.toggle("active");
}

function toggleRecipePopup(dishId) {
    document.getElementById("recipe-popup-" + dishId).classList.toggle("active");
}
document.addEventListener('DOMContentLoaded', function () {
    // Check if the "popup" query parameter exists
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('popup')) {
        // Open the popup
        togglePopup();
    }
});