//document.addEventListener('DOMContentLoaded', function () {
//    const radioButtons = document.querySelectorAll('input[name="selected_date"]');    
//     radioButtons.forEach(button => {
//         button.addEventListener('change', function() {
//             // Submit the form immediately when a radio button is selected
//             if (button.checked) {
//                 document.querySelector('#filter-form').submit();  // Submit the form
//             }
//         });
//     });
// });
document.addEventListener('DOMContentLoaded', function () {
    const submitRatingButtons = document.querySelectorAll('.submit-rating');

    submitRatingButtons.forEach(button => {
        button.addEventListener('click', function () {
            const menuLine = this.getAttribute('data-menu-line');
            const id = this.getAttribute('data-id');
            const rating = document.querySelector(`input[name="rating_${menuLine}"]:checked`).value;

            if (rating) {
                // Display the "Rating received" message
                const feedback = this.nextElementSibling;
                feedback.classList.remove('hidden');
                feedback.textContent = 'Rating received!';
                
                // Optionally, clear the feedback after a few seconds
                setTimeout(() => {
                    feedback.classList.add('hidden');
                }, 3000);
            } else {
                alert('Please select a rating before submitting.');
            }

            const formData = new FormData();
            //formData.append('rating_menu_line', menuLine);
            formData.append('id', id);
            formData.append('rating', rating);

            fetch('/menu', {
                method: 'POST',
                body: formData,
            })
        });
    });
});

document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        if (this.checked) {
            if (this.name === 'selected_diet') {  // Remove 'selected_price' from here
                document.querySelectorAll(`input[name="${this.name}"]`).forEach(cb => {
                    if (cb !== this) cb.checked = false;
                });
            }     
        }
    });
});