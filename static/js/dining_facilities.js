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

            const formData = new FormData();
            //formData.append('rating_menu_line', menuLine);
            formData.append('id', id);
            formData.append('rating', rating);

            fetch('/dining_facilities', {
                method: 'POST',
                body: formData,
            })
        });
    });
});