const removeDishButtons = document.querySelectorAll('.remove-dish-button');

removeDishButtons.forEach(button => {
    button.addEventListener('click', function () {
        const menuId = this.getAttribute('data-id');
        const formData = new FormData();
        formData.append('menu_id', menuId);

        fetch('/user', {
            method: 'POST',
            body: formData,
        })
        window.location.reload()
    });
});