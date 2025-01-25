document.addEventListener('DOMContentLoaded', function () {
    const submitRatingButtons = document.querySelectorAll('.submit-rating');
    const mensaDropdown = document.getElementById('mensa-dropdown');
    const expandButtons = document.querySelectorAll('.expand-button');

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
            // Call the function to display the success message
            showRatingFeedback();          
        });
    });

    // Handle mensa selection
    //mensaDropdown.addEventListener('change', function() {
    //    const form = document.getElementById('filter-form');
    //    if (this.value === 'all') {
    //        // Submit form to refresh with all mensa results
    //        form.submit();
    //    }
    //});

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


function showRatingFeedback() {
    var feedbackElement = document.getElementById('rating-feedback');
    feedbackElement.classList.remove('hidden');
    setTimeout(function() {
        feedbackElement.classList.add('hidden');
    }, 3000); // Hide after 3 seconds
}