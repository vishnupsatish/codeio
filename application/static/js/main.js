function removeActive(elem) {
    document.querySelector("#" + elem.getAttribute('data-target')).classList.remove('is-active');
}

function toggleActive(elem) {
    document.querySelector("#" + elem.getAttribute('data-target')).classList.toggle('is-active');
}

