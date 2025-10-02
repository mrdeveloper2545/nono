document.addEventListener('DOMContentLoaded', function () {
    {% if messages_count > 0 %}
    var notificationDropdown = document.getElementById('notificationDropdown');
    if (notificationDropdown) {
        notificationDropdown.click(); // Open the dropdown
    }
    {% endif %}
});


