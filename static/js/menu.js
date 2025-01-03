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
            //const menuLine = this.getAttribute('data-menu-line');
            const id = this.getAttribute('data-id');
            const rating = document.querySelector(`input[name="rating_${id}"]:checked`).value;

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
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                // After the POST request, send a GET request to fetch the updated random dish
                return fetch('/menu');
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                // After the POST request, send a GET request to fetch the updated random dish
                return fetch('/menu', {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
            })
            .then(response => response.json())
            .then(data => {
                // Update the random_dish variable
                data = data.random_dish;
                // Update the button attributes dynamically
                const submitButton = document.querySelector('.submit-rating');
                submitButton.setAttribute('data-id', data.id); // Update data-id
                document.getElementById('random-dish-name').textContent = data.name;

            
                // Update other dependent elements if necessary
                const popupContent = document.getElementById('popup-content');
                popupContent.innerHTML = `
                    <input type="radio" id="star5_${data.id}" name="rating_${data.id}" value="5" />
                    <label for="star5_${data.id}">&#9733;</label>
                    <input type="radio" id="star4_${data.id}" name="rating_${data.id}" value="4" />
                    <label for="star4_${data.id}">&#9733;</label>
                    <input type="radio" id="star3_${data.id}" name="rating_${data.id}" value="3" />
                    <label for="star3_${data.id}">&#9733;</label>
                    <input type="radio" id="star2_${data.id}" name="rating_${data.id}" value="2" />
                    <label for="star2_${data.id}">&#9733;</label>
                    <input type="radio" id="star1_${data.id}" name="rating_${data.id}" value="1" />
                    <label for="star1_${data.id}">&#9733;</label>
                `;
            })
            .catch(error => console.error('Error:', error));
                      
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