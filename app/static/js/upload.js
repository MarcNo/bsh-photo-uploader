/* upload.js — drag-drop preview + XHR upload with progress */
(function () {
  'use strict';

  const dropZone     = document.getElementById('drop-zone');
  const fileInput    = document.getElementById('file-input');
  const previewArea  = document.getElementById('preview-area');
  const uploadActions= document.getElementById('upload-actions');
  const submitBtn    = document.getElementById('submit-btn');
  const clearBtn     = document.getElementById('clear-btn');
  const fileCountEl  = document.getElementById('file-count');
  const progressWrap = document.getElementById('progress-bar-wrap');
  const progressFill = document.getElementById('progress-fill');
  const progressLbl  = document.getElementById('progress-label');
  const form         = document.getElementById('upload-form');

  let selectedFiles = [];

  // ── Drag and drop ──────────────────────────────────────────
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  ['dragleave', 'dragend'].forEach(evt =>
    dropZone.addEventListener(evt, () => dropZone.classList.remove('drag-over'))
  );
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    addFiles(Array.from(e.dataTransfer.files));
  });

  // ── File input change ──────────────────────────────────────
  fileInput.addEventListener('change', () => {
    addFiles(Array.from(fileInput.files));
    fileInput.value = '';
  });

  // ── Add & preview files ────────────────────────────────────
  function addFiles(files) {
    files.forEach(f => {
      if (!selectedFiles.find(x => x.name === f.name && x.size === f.size)) {
        selectedFiles.push(f);
        renderPreview(f);
      }
    });
    updateUI();
  }

  function renderPreview(file) {
    const item = document.createElement('div');
    item.className = 'preview-item';
    item.dataset.name = file.name;
    item.dataset.size = file.size;

    const isVideo = file.type.startsWith('video/');
    const media = document.createElement(isVideo ? 'video' : 'img');
    media.src = URL.createObjectURL(file);
    if (isVideo) { media.muted = true; media.preload = 'metadata'; }
    item.appendChild(media);

    const name = document.createElement('span');
    name.className = 'preview-name';
    name.textContent = file.name;
    item.appendChild(name);

    const rm = document.createElement('button');
    rm.className = 'preview-remove';
    rm.type = 'button';
    rm.textContent = '✕';
    rm.addEventListener('click', () => removeFile(file, item));
    item.appendChild(rm);

    previewArea.appendChild(item);
  }

  function removeFile(file, el) {
    selectedFiles = selectedFiles.filter(f => !(f.name === file.name && f.size === file.size));
    URL.revokeObjectURL(el.querySelector('img, video')?.src);
    el.remove();
    updateUI();
  }

  function updateUI() {
    const count = selectedFiles.length;
    if (count > 0) {
      previewArea.classList.remove('hidden');
      uploadActions.classList.remove('hidden');
      fileCountEl.textContent = `${count} file${count !== 1 ? 's' : ''}`;
    } else {
      previewArea.classList.add('hidden');
      uploadActions.classList.add('hidden');
    }
  }

  // ── Clear ──────────────────────────────────────────────────
  clearBtn.addEventListener('click', () => {
    selectedFiles = [];
    previewArea.innerHTML = '';
    updateUI();
  });

  // ── Submit via XHR for progress ───────────────────────────
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!selectedFiles.length) return;

    const fd = new FormData();
    selectedFiles.forEach(f => fd.append('files', f));

    const xhr = new XMLHttpRequest();
    xhr.open('POST', form.action, true);

    progressWrap.classList.remove('hidden');
    submitBtn.disabled = true;
    clearBtn.disabled = true;

    xhr.upload.addEventListener('progress', (ev) => {
      if (ev.lengthComputable) {
        const pct = Math.round((ev.loaded / ev.total) * 100);
        progressFill.style.width = pct + '%';
        progressLbl.textContent = `Uploading… ${pct}%`;
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 400) {
        // Follow redirect
        window.location.href = xhr.responseURL || '/gallery';
      } else {
        progressLbl.textContent = 'Upload failed. Please try again.';
        submitBtn.disabled = false;
        clearBtn.disabled = false;
      }
    });

    xhr.addEventListener('error', () => {
      progressLbl.textContent = 'Network error. Please try again.';
      submitBtn.disabled = false;
      clearBtn.disabled = false;
    });

    xhr.send(fd);
  });
})();
