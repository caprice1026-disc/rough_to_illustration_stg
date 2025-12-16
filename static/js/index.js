const initCounters = () => {
  const updateCounter = (textarea) => {
    const targetId = textarea.dataset.counterTarget;
    if (!targetId) return;
    const target = document.getElementById(targetId);
    if (!target) return;
    const max = textarea.getAttribute('maxlength') || textarea.maxLength;
    target.textContent = `${textarea.value.length}/${max}`;
  };

  document.querySelectorAll('[data-counter-target]').forEach((el) => {
    updateCounter(el);
    el.addEventListener('input', () => updateCounter(el));
  });
};

const bindImageUploader = (config) => {
  const fileInput = document.getElementById(config.inputId);
  const previewImage = document.getElementById(config.previewId);
  const placeholder = document.getElementById(config.placeholderId);
  const fileMeta = document.getElementById(config.metaId);
  const dropzone = document.getElementById(config.dropzoneId);
  const clearButton = document.getElementById(config.clearButtonId);

  if (!fileInput || !previewImage || !placeholder || !fileMeta || !dropzone || !clearButton) return null;

  const resetPreview = () => {
    previewImage.classList.add('d-none');
    previewImage.removeAttribute('src');
    placeholder.classList.remove('d-none');
    fileMeta.textContent = '';
    fileInput.value = '';
  };

  const handleFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      previewImage.src = event.target.result;
      previewImage.classList.remove('d-none');
      placeholder.classList.add('d-none');
      const sizeKb = (file.size / 1024).toFixed(1);
      fileMeta.textContent = `${file.name} / ${sizeKb} KB`;
    };
    reader.readAsDataURL(file);
  };

  clearButton.addEventListener('click', resetPreview);

  fileInput.addEventListener('change', (event) => {
    const [file] = event.target.files;
    handleFile(file);
  });

  ['dragenter', 'dragover'].forEach((type) => {
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.add('hover');
    });
  });

  ['dragleave', 'drop'].forEach((type) => {
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.remove('hover');
    });
  });

  dropzone.addEventListener('drop', (event) => {
    const [file] = event.dataTransfer.files;
    if (!file) return;
    fileInput.files = event.dataTransfer.files;
    handleFile(file);
  });

  return { resetPreview };
};

const initImagePreviews = () => {
  const uploaders = {
    rough: bindImageUploader({
      inputId: 'rough_image',
      previewId: 'roughPreviewImage',
      placeholderId: 'roughPlaceholder',
      metaId: 'roughFileMeta',
      dropzoneId: 'roughDropzone',
      clearButtonId: 'roughClearImage',
    }),
    reference: bindImageUploader({
      inputId: 'reference_image',
      previewId: 'referencePreviewImage',
      placeholderId: 'referencePlaceholder',
      metaId: 'referenceFileMeta',
      dropzoneId: 'referenceDropzone',
      clearButtonId: 'referenceClearImage',
    }),
  };

  return uploaders;
};

const MODE_SUBMIT_LABELS = {
  rough_with_instructions: 'イラスト生成をリクエスト',
  reference_style_colorize: '参照して着色をリクエスト',
  chat_edit: 'チャット編集（準備中）',
};

const initModeSwitch = (uploaders) => {
  const modePills = document.getElementById('modePills');
  const modeInput = document.getElementById('generationModeInput');
  const modeDescription = document.getElementById('modeDescription');
  const submitLabel = document.getElementById('submitLabel');

  if (!modePills || !modeInput) return;

  const splitModes = (raw) =>
    String(raw || '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);

  const setModeInUrl = (modeId) => {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('mode', modeId);
      window.history.replaceState({}, '', url);
    } catch (error) {
      console.warn('Failed to update mode in URL', error);
    }
  };

  const toggleVisibility = (modeId) => {
    document.querySelectorAll('[data-mode-visible]').forEach((el) => {
      const modes = splitModes(el.dataset.modeVisible);
      const shouldShow = modes.includes(modeId);
      el.classList.toggle('d-none', !shouldShow);
    });
  };

  const applyMode = (modeId, { updateUrl = true } = {}) => {
    modeInput.value = modeId;
    document.querySelectorAll('input[name="mode"]').forEach((input) => {
      input.value = modeId;
    });

    const buttons = modePills.querySelectorAll('button[data-mode]');
    buttons.forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.mode === modeId);
    });

    toggleVisibility(modeId);

    if (submitLabel && MODE_SUBMIT_LABELS[modeId]) {
      submitLabel.textContent = MODE_SUBMIT_LABELS[modeId];
    }

    const activeButton = modePills.querySelector(`button[data-mode="${modeId}"]`);
    const description = activeButton ? activeButton.dataset.modeDescription : '';
    if (modeDescription) modeDescription.textContent = description || '';

    if (uploaders && uploaders.reference && modeId !== 'reference_style_colorize') {
      uploaders.reference.resetPreview();
    }

    if (updateUrl) setModeInUrl(modeId);
  };

  modePills.querySelectorAll('button[data-mode]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (btn.disabled) return;
      applyMode(btn.dataset.mode);
    });
  });

  applyMode(modeInput.value, { updateUrl: false });
};

const initSubmitState = () => {
  const form = document.getElementById('generateForm');
  const submitBtn = document.getElementById('generateButton');
  const spinner = document.getElementById('loadingSpinner');
  const submitLabel = document.getElementById('submitLabel');
  const statusBadge = document.getElementById('generationStatusBadge');
  const statusText = document.getElementById('generationStatusText');

  if (!form || !submitBtn || !spinner || !submitLabel) return;

  form.addEventListener('submit', () => {
    submitBtn.disabled = true;
    spinner.classList.remove('d-none');
    submitLabel.textContent = '送信中...';
    if (statusBadge) statusBadge.textContent = '生成中';
    if (statusText) statusText.textContent = '生成中です。しばらくお待ちください。';
  });
};

const initPresets = () => {
  const panel = document.getElementById('presetPanel');
  const presetSelect = document.getElementById('presetSelect');
  const deletePresetId = document.getElementById('deletePresetId');
  const applyButton = document.getElementById('applyPreset');
  const presetCreateForm = document.getElementById('presetCreateForm');
  const presetColorInput = document.getElementById('preset_color_value');
  const presetPoseInput = document.getElementById('preset_pose_value');
  const colorTextarea = document.getElementById('color_instruction');
  const poseTextarea = document.getElementById('pose_instruction');

  if (!panel || !presetSelect || !deletePresetId || !applyButton || !presetCreateForm || !presetColorInput || !presetPoseInput || !colorTextarea || !poseTextarea) {
    return;
  }

  let presets = [];
  try {
    const raw = panel.dataset.presets || '[]';
    presets = JSON.parse(raw);
  } catch (error) {
    console.error('プリセットの読み込みに失敗しました', error);
  }

  const findPreset = (presetId) => presets.find((preset) => String(preset.id) === String(presetId));

  const applyPreset = () => {
    const selected = findPreset(presetSelect.value);
    if (!selected) return;

    colorTextarea.value = selected.color || '';
    poseTextarea.value = selected.pose || '';
    colorTextarea.dispatchEvent(new Event('input'));
    poseTextarea.dispatchEvent(new Event('input'));
  };

  const syncDeleteField = () => {
    deletePresetId.value = presetSelect.value || '';
  };

  presetSelect.addEventListener('change', syncDeleteField);
  applyButton.addEventListener('click', applyPreset);
  syncDeleteField();

  presetCreateForm.addEventListener('submit', () => {
    // 現在のテキストエリア内容をプリセットとして保存する
    presetColorInput.value = colorTextarea.value;
    presetPoseInput.value = poseTextarea.value;
  });
};

const bootstrapIndexPage = () => {
  initCounters();
  const uploaders = initImagePreviews();
  initModeSwitch(uploaders);
  initSubmitState();
  initPresets();
};

document.addEventListener('DOMContentLoaded', bootstrapIndexPage);
