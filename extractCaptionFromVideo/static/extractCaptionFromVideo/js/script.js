var elements = document.getElementsByClassName('clickable');

var goToLink = function() {
  console.log(this);
  window.document.location = this.getAttribute("data-href");
};


Array.from(elements, e =>
    e.addEventListener('click', goToLink)
);
