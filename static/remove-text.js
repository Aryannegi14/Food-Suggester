// Wait for the DOM to fully load
document.addEventListener('DOMContentLoaded', function() {
    // Select the element containing the unwanted text
    const unwantedText = document.querySelector('.dish-list + p') || document.querySelector('p:contains("Here are 5 dish suggestions using")');

    // Remove the element if found
    if (unwantedText) {
        unwantedText.remove();
    }
});

// Polyfill for :contains (if not supported by the browser)
if (!document.querySelector(':contains')) {
    document.querySelector = function(selectors) {
        const elements = document.querySelectorAll(selectors);
        return elements.length ? elements[0] : null;
    };
}