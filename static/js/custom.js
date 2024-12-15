function sendDishData(restaurant, day) {
    // First, send the data to the server (POST request)
    fetch('/dish-clicked', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `mensa_name=${encodeURIComponent(restaurant)}&mensa_day=${encodeURIComponent(day)}`
    })
    .then(response => response.json())  // Handle response
    .then(data => {
        console.log(data);  // Log the response for debugging
        if (data.success) {
            // Redirect directly to mensa_menu route with the query params
            window.location.href = `/mensa_menu?mensa_name=${encodeURIComponent(restaurant)}&mensa_day=${encodeURIComponent(day)}`;
        }
    })
    .catch(error => console.error('Error:', error));  // Handle any error
}