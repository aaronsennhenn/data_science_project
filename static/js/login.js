function setActionForm(action) {
    let form = document.getElementById('auth-form');
    if (action === 'login') {
        form.action = "{{ url_for('login') }}";
        form.method = 'post';
        form.submit();
    } else if (action === 'register') {
        form.action = "{{ url_for('register') }}";
        form.method = 'post';
        form.submit();
    }
}