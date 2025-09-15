document.addEventListener('DOMContentLoaded', () => {
  const fileInputs = document.querySelectorAll('.file-label input[type="file"]');
  fileInputs.forEach((input) => {
    input.addEventListener('change', () => {
      const label = input.closest('.file-label');
      const fileName = input.files && input.files.length ? input.files[0].name : 'No file selected';
      const chosen = label?.querySelector('.file-chosen');
      if (chosen) {
        chosen.textContent = fileName;
      }
    });
  });

  const flashes = document.querySelectorAll('.flash');
  flashes.forEach((flash) => {
    setTimeout(() => {
      flash.classList.add('fade-out');
      flash.addEventListener('transitionend', () => flash.remove(), { once: true });
    }, 4200);
  });

  const confirmForms = document.querySelectorAll('form[data-confirm]');
  confirmForms.forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.dataset.confirm || 'Are you sure?';
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
});
