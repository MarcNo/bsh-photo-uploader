/* gallery.js — inline title/caption save and delete */
(function () {
  'use strict';

  // ── Save button ───────────────────────────────────────────
  document.querySelectorAll('.btn-save').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id    = btn.dataset.id;
      const card  = btn.closest('.gallery-card');
      const title = card.querySelector('.meta-title').value.trim();
      const cap   = card.querySelector('.meta-caption').value.trim();

      btn.textContent = 'Saving…';
      btn.disabled = true;

      try {
        const res = await fetch('/update-media', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, title, caption: cap })
        });
        const data = await res.json();
        if (data.ok) {
          btn.textContent = 'Saved ✓';
          setTimeout(() => { btn.textContent = 'Save'; btn.disabled = false; }, 2000);
        } else {
          btn.textContent = 'Error';
          btn.disabled = false;
        }
      } catch {
        btn.textContent = 'Error';
        btn.disabled = false;
      }
    });
  });

  // ── Delete button ─────────────────────────────────────────
  document.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Delete this file? This cannot be undone.')) return;

      const id   = btn.dataset.id;
      const card = btn.closest('.gallery-card');

      try {
        const res = await fetch('/delete-media', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        const data = await res.json();
        if (data.ok) {
          card.style.opacity = '0';
          card.style.transform = 'scale(0.9)';
          card.style.transition = 'opacity 0.3s, transform 0.3s';
          setTimeout(() => card.remove(), 300);
        }
      } catch {
        alert('Could not delete the file. Please try again.');
      }
    });
  });
})();
