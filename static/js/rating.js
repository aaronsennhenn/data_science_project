document.addEventListener('DOMContentLoaded', function () {
    const submitRatingButtons = document.querySelectorAll('.submit-rating');

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
            });
        });
    });

    // Check if the "popup" query parameter exists
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('popup')) {
        // Open the popup
        togglePopup();
    }
});

// Function for rate more dishes popup
function togglePopup() {
    document.getElementById("popup-1").classList.toggle("active");
}