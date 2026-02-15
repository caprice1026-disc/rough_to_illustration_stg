const state = {
  user: null,
  modes: [],
  chatModes: [],
  options: { aspect_ratio_options: [], resolution_options: [] },
  presets: [],
  sessions: [],
  currentSessionId: null,
  currentView: 'generate',
  lastResult: null,
  csrfToken: null,
  adminUsers: [],
  chatEnabled: true,
  uploadPreviewObjectUrls: { rough: null, referenceRough: null },
  imageViewerModal: null,
};

const elements = {};

const cacheElements = () => {
  elements.statusArea = document.getElementById('statusArea');
  elements.loginView = document.getElementById('loginView');
  elements.appView = document.getElementById('appView');
  elements.loginForm = document.getElementById('loginForm');
  elements.loginUsername = document.getElementById('loginUsername');
  elements.loginPassword = document.getElementById('loginPassword');
  elements.navUserBadge = document.getElementById('navUserBadge');
  elements.navViews = document.getElementById('navViews');
  elements.navChatButton = document.getElementById('navChatButton');
  elements.navAccountButton = document.getElementById('navAccountButton');
  elements.navAdminButton = document.getElementById('navAdminButton');
  elements.logoutButton = document.getElementById('logoutButton');
  elements.generateView = document.getElementById('generateView');
  elements.chatView = document.getElementById('chatView');
  elements.accountView = document.getElementById('accountView');
  elements.adminView = document.getElementById('adminView');
  elements.generationMode = document.getElementById('generationMode');
  elements.generationModeDescription = document.getElementById('generationModeDescription');
  elements.generateForm = document.getElementById('generateForm');
  elements.generateSpinner = document.getElementById('generateSpinner');
  elements.generateButtonLabel = document.getElementById('generateButtonLabel');
  elements.generationStatusBadge = document.getElementById('generationStatusBadge');
  elements.generationOptions = document.getElementById('generationOptions');
  elements.aspectRatioSelect = document.getElementById('aspectRatioSelect');
  elements.resolutionSelect = document.getElementById('resolutionSelect');
  elements.roughImageInput = document.getElementById('roughImageInput');
  elements.referenceRoughInput = document.getElementById('referenceRoughInput');
  elements.roughUploadPreview = document.getElementById('roughUploadPreview');
  elements.roughUploadPreviewImage = document.getElementById('roughUploadPreviewImage');
  elements.roughUploadPreviewMeta = document.getElementById('roughUploadPreviewMeta');
  elements.referenceRoughUploadPreview = document.getElementById('referenceRoughUploadPreview');
  elements.referenceRoughPreviewImage = document.getElementById('referenceRoughPreviewImage');
  elements.referenceRoughPreviewMeta = document.getElementById('referenceRoughPreviewMeta');
  elements.resultImage = document.getElementById('resultImage');
  elements.resultImageHint = document.getElementById('resultImageHint');
  elements.resultPlaceholder = document.getElementById('resultPlaceholder');
  elements.downloadLink = document.getElementById('downloadLink');
  elements.imageViewerModal = document.getElementById('imageViewerModal');
  elements.imageViewerModalBody = document.querySelector('#imageViewerModal .image-viewer-modal-body');
  elements.imageViewerImage = document.getElementById('imageViewerImage');
  elements.presetSelect = document.getElementById('presetSelect');
  elements.applyPreset = document.getElementById('applyPreset');
  elements.deletePreset = document.getElementById('deletePreset');
  elements.presetForm = document.getElementById('presetForm');
  elements.presetName = document.getElementById('presetName');
  elements.chatSessionList = document.getElementById('chatSessionList');
  elements.newSessionButton = document.getElementById('newSessionButton');
  elements.chatMessages = document.getElementById('chatMessages');
  elements.chatForm = document.getElementById('chatForm');
  elements.chatSessionId = document.getElementById('chatSessionId');
  elements.chatModeSelect = document.getElementById('chatModeSelect');
  elements.chatModeHelper = document.getElementById('chatModeHelper');
  elements.currentSessionBadge = document.getElementById('currentSessionBadge');
  elements.chatStatus = document.getElementById('chatStatus');
  elements.chatMessage = document.getElementById('chatMessage');
  elements.chatImages = document.getElementById('chatImages');
  elements.accountUsername = document.getElementById('accountUsername');
  elements.accountEmail = document.getElementById('accountEmail');
  elements.accountRole = document.getElementById('accountRole');
  elements.accountPasswordForm = document.getElementById('accountPasswordForm');
  elements.accountCurrentPassword = document.getElementById('accountCurrentPassword');
  elements.accountNewPassword = document.getElementById('accountNewPassword');
  elements.accountNewPasswordConfirm = document.getElementById('accountNewPasswordConfirm');
  elements.signupForm = document.getElementById('signupForm');
  elements.signupUsername = document.getElementById('signupUsername');
  elements.signupEmail = document.getElementById('signupEmail');
  elements.signupPassword = document.getElementById('signupPassword');
  elements.adminSelfPasswordForm = document.getElementById('adminSelfPasswordForm');
  elements.adminSelfCurrentPassword = document.getElementById('adminSelfCurrentPassword');
  elements.adminSelfNewPassword = document.getElementById('adminSelfNewPassword');
  elements.adminSelfNewPasswordConfirm = document.getElementById('adminSelfNewPasswordConfirm');
  elements.adminUserTableBody = document.getElementById('adminUserTableBody');
  elements.adminRefreshButton = document.getElementById('adminRefreshButton');
};

const showStatus = (message, type = 'info') => {
  if (!elements.statusArea) return;
  const wrapper = document.createElement('div');
  wrapper.className = `alert alert-${type} alert-dismissible fade show flash-card`;
  wrapper.setAttribute('role', 'alert');
  wrapper.innerHTML = `<i class="bi bi-info-circle me-2"></i>${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
  elements.statusArea.appendChild(wrapper);
  setTimeout(() => {
    try {
      const alertApi = window.bootstrap?.Alert;
      if (alertApi) {
        const alertInstance = alertApi.getOrCreateInstance(wrapper);
        alertInstance.close();
      } else {
        wrapper.remove();
      }
    } catch (error) {
      wrapper.remove();
    }
  }, 5200);
};

const clearStatus = () => {
  if (!elements.statusArea) return;
  elements.statusArea.innerHTML = '';
};

const formatFileSize = (byteSize) => {
  if (!Number.isFinite(byteSize) || byteSize < 0) return '0 B';
  if (byteSize < 1024) return `${byteSize} B`;
  if (byteSize < 1024 * 1024) return `${(byteSize / 1024).toFixed(1)} KB`;
  return `${(byteSize / (1024 * 1024)).toFixed(2)} MB`;
};

const releasePreviewObjectUrl = (slot) => {
  const currentUrl = state.uploadPreviewObjectUrls[slot];
  if (!currentUrl) return;
  URL.revokeObjectURL(currentUrl);
  state.uploadPreviewObjectUrls[slot] = null;
};

const disposeUploadPreviewUrls = () => {
  releasePreviewObjectUrl('rough');
  releasePreviewObjectUrl('referenceRough');
};

const resetUploadPreview = ({ previewWrap, previewImage, previewMeta, slot }) => {
  releasePreviewObjectUrl(slot);
  if (previewImage) previewImage.removeAttribute('src');
  if (previewMeta) previewMeta.textContent = '';
  if (previewWrap) previewWrap.classList.add('d-none');
};

const updateUploadPreview = ({ file, previewWrap, previewImage, previewMeta, slot }) => {
  if (!file || !previewWrap || !previewImage) {
    resetUploadPreview({ previewWrap, previewImage, previewMeta, slot });
    return;
  }
  releasePreviewObjectUrl(slot);
  const objectUrl = URL.createObjectURL(file);
  state.uploadPreviewObjectUrls[slot] = objectUrl;
  previewImage.src = objectUrl;
  if (previewMeta) {
    previewMeta.textContent = `${file.name} (${formatFileSize(file.size)})`;
  }
  previewWrap.classList.remove('d-none');
};

const bindRoughUploadPreview = ({ input, previewWrap, previewImage, previewMeta, slot }) => {
  if (!input) return;
  const sync = () => {
    const [file] = input.files || [];
    updateUploadPreview({
      file,
      previewWrap,
      previewImage,
      previewMeta,
      slot,
    });
  };
  input.addEventListener('change', sync);
  sync();
};

const initRoughUploadPreviews = () => {
  bindRoughUploadPreview({
    input: elements.roughImageInput,
    previewWrap: elements.roughUploadPreview,
    previewImage: elements.roughUploadPreviewImage,
    previewMeta: elements.roughUploadPreviewMeta,
    slot: 'rough',
  });
  bindRoughUploadPreview({
    input: elements.referenceRoughInput,
    previewWrap: elements.referenceRoughUploadPreview,
    previewImage: elements.referenceRoughPreviewImage,
    previewMeta: elements.referenceRoughPreviewMeta,
    slot: 'referenceRough',
  });
  window.addEventListener('beforeunload', disposeUploadPreviewUrls);
};

const openResultImageViewer = () => {
  if (!elements.resultImage || elements.resultImage.classList.contains('d-none')) return;
  const src = elements.resultImage.getAttribute('src') || '';
  if (!src || !elements.imageViewerImage) return;

  elements.imageViewerImage.src = src;
  elements.imageViewerImage.alt = elements.resultImage.alt || '生成画像の拡大表示';

  if (state.imageViewerModal) {
    state.imageViewerModal.show();
    return;
  }
  if (!window.bootstrap || !elements.imageViewerModal) return;
  state.imageViewerModal = window.bootstrap.Modal.getOrCreateInstance(elements.imageViewerModal);
  state.imageViewerModal.show();
};

const initResultImageViewer = () => {
  if (window.bootstrap && elements.imageViewerModal) {
    state.imageViewerModal = window.bootstrap.Modal.getOrCreateInstance(elements.imageViewerModal);
    elements.imageViewerModal.addEventListener('hidden.bs.modal', () => {
      if (elements.imageViewerImage) elements.imageViewerImage.removeAttribute('src');
    });
  }

  const isClickInsideRenderedImage = (event) => {
    if (!elements.imageViewerImage) return false;
    if (event.target !== elements.imageViewerImage) return false;

    const image = elements.imageViewerImage;
    const rect = image.getBoundingClientRect();
    if (!rect.width || !rect.height) return false;
    const relativeX = event.clientX - rect.left;
    const relativeY = event.clientY - rect.top;

    const naturalWidth = image.naturalWidth || 0;
    const naturalHeight = image.naturalHeight || 0;
    if (!naturalWidth || !naturalHeight) return true;

    const imageAspect = naturalWidth / naturalHeight;
    const boxAspect = rect.width / rect.height;

    let renderedWidth = rect.width;
    let renderedHeight = rect.height;
    let offsetX = 0;
    let offsetY = 0;

    if (boxAspect > imageAspect) {
      renderedWidth = rect.height * imageAspect;
      offsetX = (rect.width - renderedWidth) / 2;
    } else {
      renderedHeight = rect.width / imageAspect;
      offsetY = (rect.height - renderedHeight) / 2;
    }

    return (
      relativeX >= offsetX &&
      relativeX <= offsetX + renderedWidth &&
      relativeY >= offsetY &&
      relativeY <= offsetY + renderedHeight
    );
  };

  if (elements.imageViewerModalBody) {
    elements.imageViewerModalBody.addEventListener('click', (event) => {
      if (!state.imageViewerModal) return;
      if (isClickInsideRenderedImage(event)) return;
      state.imageViewerModal.hide();
    });
  }
  if (!elements.resultImage) return;
  elements.resultImage.addEventListener('click', openResultImageViewer);
  elements.resultImage.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    openResultImageViewer();
  });
};

const fetchCsrfToken = async () => {
  const response = await fetch('/api/csrf', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  const payload = await response.json();
  state.csrfToken = payload.csrf_token || null;
  return state.csrfToken;
};

const ensureCsrfToken = async () => {
  if (state.csrfToken) return state.csrfToken;
  return fetchCsrfToken();
};

const apiFetch = async (url, options = {}) => {
  const headers = options.headers ? { ...options.headers } : {};
  const method = (options.method || 'GET').toUpperCase();
  const retryingCsrf = Boolean(options._csrfRetry);
  const fetchOptions = { ...options };
  delete fetchOptions._csrfRetry;
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = await ensureCsrfToken();
    if (token) headers['X-CSRFToken'] = token;
  }
  if (!(fetchOptions.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  headers['Accept'] = headers['Accept'] || 'application/json';

  const response = await fetch(url, {
    credentials: 'same-origin',
    ...fetchOptions,
    headers,
  });

  const contentType = response.headers.get('content-type') || '';
  const hasJson = contentType.includes('application/json');
  const payload = hasJson ? await response.json() : {};

  if (response.status === 401) {
    setLoggedOut();
    throw new Error(payload.error || 'ログインが必要です。');
  }

  if (!response.ok) {
    if (
      response.status === 400 &&
      !retryingCsrf &&
      payload.error &&
      payload.error.includes('CSRF')
    ) {
      state.csrfToken = null;
      await fetchCsrfToken();
      return apiFetch(url, { ...options, _csrfRetry: true });
    }
    throw new Error(payload.error || '通信に失敗しました。');
  }

  return payload;
};

const setLoggedOut = () => {
  state.user = null;
  state.presets = [];
  state.sessions = [];
  state.currentSessionId = null;
  state.lastResult = null;
  state.csrfToken = null;
  state.adminUsers = [];
  state.chatEnabled = true;
  disposeUploadPreviewUrls();
  clearStatus();
  renderLogin();
};

const renderLogin = () => {
  if (elements.loginView) elements.loginView.classList.remove('d-none');
  if (elements.appView) elements.appView.classList.add('d-none');
  if (elements.navUserBadge) elements.navUserBadge.classList.add('d-none');
  if (elements.navViews) elements.navViews.classList.add('d-none');
  if (elements.logoutButton) elements.logoutButton.classList.add('d-none');
};

const renderAccountProfile = () => {
  if (!state.user) return;
  if (elements.accountUsername) elements.accountUsername.value = state.user.username || '';
  if (elements.accountEmail) elements.accountEmail.value = state.user.email || '';
  if (elements.accountRole) elements.accountRole.value = state.user.is_admin ? 'admin' : 'user';
};

const renderApp = () => {
  if (elements.loginView) elements.loginView.classList.add('d-none');
  if (elements.appView) elements.appView.classList.remove('d-none');
  if (elements.navUserBadge && state.user) {
    elements.navUserBadge.textContent = `${state.user.username} さん`;
    elements.navUserBadge.classList.remove('d-none');
  }
  if (elements.navViews) elements.navViews.classList.remove('d-none');
  if (elements.logoutButton) elements.logoutButton.classList.remove('d-none');
  if (elements.adminView) {
    elements.adminView.classList.toggle('d-none', !state.user?.is_admin);
  }
  if (elements.navChatButton) {
    elements.navChatButton.classList.toggle('d-none', !state.chatEnabled);
  }
  if (elements.navAccountButton) {
    elements.navAccountButton.classList.toggle('d-none', Boolean(state.user?.is_admin));
  }
  if (elements.navAdminButton) {
    elements.navAdminButton.classList.toggle('d-none', !state.user?.is_admin);
  }
  renderAccountProfile();
  setView(state.currentView);
  if (state.user?.is_admin) {
    loadAdminUsers();
  }
};

const setView = (viewName) => {
  let nextView = viewName;
  if (nextView === 'admin' && !state.user?.is_admin) {
    nextView = 'generate';
  }
  if (nextView === 'account' && (!state.user || state.user.is_admin)) {
    nextView = state.user?.is_admin ? 'admin' : 'generate';
  }
  if (nextView === 'chat' && !state.chatEnabled) {
    nextView = 'generate';
  }
  state.currentView = nextView;
  if (elements.generateView) elements.generateView.classList.toggle('d-none', nextView !== 'generate');
  if (elements.chatView) elements.chatView.classList.toggle('d-none', nextView !== 'chat');
  if (elements.accountView) elements.accountView.classList.toggle('d-none', nextView !== 'account');
  if (elements.adminView) elements.adminView.classList.toggle('d-none', nextView !== 'admin');
  if (elements.navViews) {
    elements.navViews.querySelectorAll('button[data-view]').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.view === nextView);
    });
  }
  if (nextView === 'chat') {
    ensureChatReady();
  }
  if (nextView === 'admin') {
    loadAdminUsers();
  }
};

const populateModes = () => {
  if (!elements.generationMode) return;
  elements.generationMode.innerHTML = '';
  state.modes
    .filter((mode) => mode.enabled && mode.id !== 'chat_mode')
    .forEach((mode) => {
      const option = document.createElement('option');
      option.value = mode.id;
      option.textContent = mode.label;
      elements.generationMode.appendChild(option);
    });
};

const populateChatModes = () => {
  if (!elements.chatModeSelect) return;
  elements.chatModeSelect.innerHTML = '';
  state.chatModes.forEach((mode) => {
    const option = document.createElement('option');
    option.value = mode.id;
    option.textContent = mode.label;
    elements.chatModeSelect.appendChild(option);
  });
};

const populateOptions = () => {
  if (elements.aspectRatioSelect) {
    elements.aspectRatioSelect.innerHTML = '';
    state.options.aspect_ratio_options.forEach((label) => {
      const option = document.createElement('option');
      option.value = label;
      option.textContent = label === 'auto' ? '自動' : label;
      elements.aspectRatioSelect.appendChild(option);
    });
  }

  if (elements.resolutionSelect) {
    elements.resolutionSelect.innerHTML = '';
    state.options.resolution_options.forEach((label) => {
      const option = document.createElement('option');
      option.value = label;
      option.textContent = label === 'auto' ? '自動' : label;
      elements.resolutionSelect.appendChild(option);
    });
  }
};

const updateModePanels = (modeId) => {
  const panels = document.querySelectorAll('[data-mode-panel]');
  panels.forEach((panel) => {
    const isActive = panel.dataset.modePanel === modeId;
    panel.classList.toggle('d-none', !isActive);
    panel.querySelectorAll('input, textarea, select').forEach((input) => {
      input.disabled = !isActive;
    });
  });

  if (elements.generationOptions) {
    const showOptions = modeId !== 'inpaint_outpaint';
    elements.generationOptions.classList.toggle('d-none', !showOptions);
    elements.generationOptions.querySelectorAll('select').forEach((select) => {
      select.disabled = !showOptions;
    });
  }

  const description = state.modes.find((mode) => mode.id === modeId)?.description || '';
  if (elements.generationModeDescription) {
    elements.generationModeDescription.textContent = description;
  }
};

const renderPresets = () => {
  if (!elements.presetSelect) return;
  elements.presetSelect.innerHTML = '';
  if (state.presets.length === 0) {
    const option = document.createElement('option');
    option.textContent = 'プリセットなし';
    option.disabled = true;
    option.selected = true;
    elements.presetSelect.appendChild(option);
    return;
  }
  state.presets.forEach((preset) => {
    const option = document.createElement('option');
    option.value = String(preset.id);
    option.textContent = preset.name;
    elements.presetSelect.appendChild(option);
  });
};

const findPreset = () => {
  const presetId = elements.presetSelect?.value;
  if (!presetId) return null;
  return state.presets.find((preset) => String(preset.id) === String(presetId)) || null;
};

const applyPreset = () => {
  const preset = findPreset();
  if (!preset) return;

  const payload = preset.payload_json || {};
  const modeId = elements.generationMode?.value || 'rough_with_instructions';
  if (modeId === 'reference_style_colorize') {
    const referenceInstruction = document.getElementById('referenceInstruction');
    if (referenceInstruction) referenceInstruction.value = payload.reference_instruction || '';
  } else if (modeId === 'inpaint_outpaint') {
    const editInstruction = document.getElementById('editInstruction');
    const editModeSelect = document.getElementById('editModeSelect');
    if (editInstruction) editInstruction.value = payload.edit_instruction || '';
    if (editModeSelect) editModeSelect.value = payload.edit_mode || 'inpaint';
  } else {
    const colorInstruction = document.getElementById('colorInstruction');
    const poseInstruction = document.getElementById('poseInstruction');
    if (colorInstruction) colorInstruction.value = payload.color_instruction || '';
    if (poseInstruction) poseInstruction.value = payload.pose_instruction || '';
  }
};

const buildPresetPayload = () => {
  const modeId = elements.generationMode?.value || 'rough_with_instructions';
  const name = elements.presetName?.value.trim() || '';

  if (modeId === 'reference_style_colorize') {
    const referenceInstruction = document.getElementById('referenceInstruction');
    return {
      mode: modeId,
      name,
      payload_json: {
        reference_instruction: referenceInstruction?.value || '',
      },
    };
  }

  if (modeId === 'inpaint_outpaint') {
    const editInstruction = document.getElementById('editInstruction');
    const editModeSelect = document.getElementById('editModeSelect');
    return {
      mode: modeId,
      name,
      payload_json: {
        edit_instruction: editInstruction?.value || '',
        edit_mode: editModeSelect?.value || 'inpaint',
      },
    };
  }

  const colorInstruction = document.getElementById('colorInstruction');
  const poseInstruction = document.getElementById('poseInstruction');
  return {
    mode: modeId,
    name,
    payload_json: {
      color_instruction: colorInstruction?.value || '',
      pose_instruction: poseInstruction?.value || '',
    },
  };
};

const renderResult = (result) => {
  if (!elements.resultImage || !elements.resultPlaceholder || !elements.downloadLink) return;
  if (!result) {
    elements.resultImage.removeAttribute('src');
    elements.resultImage.classList.add('d-none');
    elements.resultImage.setAttribute('aria-disabled', 'true');
    elements.resultImage.tabIndex = -1;
    elements.resultPlaceholder.classList.remove('d-none');
    if (elements.resultImageHint) elements.resultImageHint.classList.add('d-none');
    elements.downloadLink.classList.add('d-none');
    return;
  }

  elements.resultPlaceholder.classList.add('d-none');
  elements.resultImage.src = result.url || '';
  elements.resultImage.classList.remove('d-none');
  elements.resultImage.setAttribute('aria-disabled', 'false');
  elements.resultImage.tabIndex = 0;
  if (elements.resultImageHint) elements.resultImageHint.classList.remove('d-none');

  const ext = result.mime_type === 'image/jpeg' ? 'jpg' : 'png';
  elements.downloadLink.href = result.download_url || result.url || '#';
  elements.downloadLink.download = `generated_image.${ext}`;
  elements.downloadLink.classList.remove('d-none');
};

const toggleGenerationLoading = (isLoading) => {
  if (elements.generateSpinner) elements.generateSpinner.classList.toggle('d-none', !isLoading);
  if (elements.generateButtonLabel) {
    elements.generateButtonLabel.textContent = isLoading ? '生成中...' : '生成をリクエスト';
  }
  if (elements.generationStatusBadge) {
    elements.generationStatusBadge.textContent = isLoading ? '生成中' : '準備完了';
  }
};

const toggleChatExtras = () => {
  if (elements.chatModeHelper) {
    elements.chatModeHelper.textContent = 'You can attach images and send text.';
  }
};

const renderChatSessions = () => {
  if (!elements.chatSessionList) return;
  elements.chatSessionList.innerHTML = '';
  state.sessions.forEach((session) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'list-group-item list-group-item-action';
    if (session.id === state.currentSessionId) item.classList.add('active');
    item.dataset.sessionId = session.id;
    item.innerHTML = `
      <div class="fw-semibold">${session.title}</div>
      <small class="text-white-50">${session.updated_at || ''}</small>
    `;
    elements.chatSessionList.appendChild(item);
  });
};

const renderChatMessages = (messages) => {
  if (!elements.chatMessages) return;
  elements.chatMessages.innerHTML = '';
  if (!messages || messages.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty-chat';
    empty.textContent = 'まだメッセージがありません。まずはテキストを送信してください。';
    elements.chatMessages.appendChild(empty);
    return;
  }
  messages.forEach((message) => {
    const wrapper = document.createElement('div');
    wrapper.className = `chat-message ${message.role === 'user' ? 'is-user' : 'is-assistant'}`;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';

    const meta = document.createElement('div');
    meta.className = 'chat-meta';
    const role = document.createElement('span');
    role.className = 'chat-role';
    role.textContent = message.role === 'user' ? 'あなた' : 'アシスタント';
    meta.appendChild(role);
    if (message.mode_id) {
      const mode = document.createElement('span');
      mode.className = 'chat-mode';
      mode.textContent = message.mode_id;
      meta.appendChild(mode);
    }
    bubble.appendChild(meta);

    if (message.text) {
      const text = document.createElement('div');
      text.className = 'chat-text';
      text.textContent = message.text;
      bubble.appendChild(text);
    }

    if (Array.isArray(message.attachments) && message.attachments.length > 0) {
      const attachmentWrap = document.createElement('div');
      attachmentWrap.className = 'chat-attachments';
      message.attachments.forEach((attachment) => {
        const card = document.createElement('div');
        card.className = 'chat-attachment';
        const img = document.createElement('img');
        img.src = attachment.url;
        img.alt = '添付画像';
        card.appendChild(img);
        const label = document.createElement('div');
        label.className = 'chat-attachment-label';
        label.textContent = attachment.kind || 'image';
        card.appendChild(label);
        attachmentWrap.appendChild(card);
      });
      bubble.appendChild(attachmentWrap);
    }

    wrapper.appendChild(bubble);
    elements.chatMessages.appendChild(wrapper);
  });
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
};

const renderAdminUsers = () => {
  if (!elements.adminUserTableBody) return;
  elements.adminUserTableBody.innerHTML = '';
  if (!state.adminUsers || state.adminUsers.length === 0) {
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="6" class="text-center text-white-50">ユーザーがいません。</td>';
    elements.adminUserTableBody.appendChild(row);
    return;
  }

  state.adminUsers.forEach((user) => {
    const row = document.createElement('tr');
    const activeLabel = user.is_active ? '有効' : '無効';
    const activeClass = user.is_active ? 'badge bg-success' : 'badge bg-secondary';
    const isSelf = state.user && user.id === state.user.id;

    row.innerHTML = `
      <td>
        <div class="fw-semibold">${user.username}</div>
        ${user.is_initial_user ? '<div class="small text-white-50">初期ユーザー</div>' : ''}
      </td>
      <td>${user.email}</td>
      <td>${user.role}</td>
      <td><span class="${activeClass}">${activeLabel}</span></td>
      <td>${user.last_login_at || '-'}</td>
      <td>
        <div class="d-flex flex-column gap-2">
          <button class="btn btn-sm btn-outline-light" data-action="toggle" data-user-id="${user.id}" ${isSelf ? 'disabled' : ''}>
            ${user.is_active ? '無効化' : '有効化'}
          </button>
          <div class="input-group input-group-sm">
            <input type="password" class="form-control" placeholder="新しいPW" data-password-input="${user.id}">
            <button class="btn btn-outline-light" type="button" data-action="reset" data-user-id="${user.id}">再設定</button>
          </div>
          ${user.role !== 'admin'
            ? `<button class="btn btn-sm btn-outline-warning" type="button" data-action="promote" data-user-id="${user.id}">admin権限を付与</button>`
            : ''}
        </div>
      </td>
    `;
    elements.adminUserTableBody.appendChild(row);
  });
};

const loadAdminUsers = async () => {
  if (!state.user?.is_admin) return;
  try {
    const payload = await apiFetch('/api/admin/users');
    state.adminUsers = payload.users || [];
    renderAdminUsers();
  } catch (error) {
    showStatus(error.message || 'ユーザー一覧の取得に失敗しました。', 'danger');
  }
};

const loadPresets = async (modeId) => {
  const payload = await apiFetch(`/api/presets?mode=${encodeURIComponent(modeId)}`);
  state.presets = payload.presets || [];
  renderPresets();
};

const loadSessions = async () => {
  const payload = await apiFetch('/api/chat/sessions');
  state.sessions = payload.sessions || [];
  if (!state.currentSessionId && state.sessions.length > 0) {
    state.currentSessionId = state.sessions[0].id;
  }
  renderChatSessions();
};

const loadSessionMessages = async (sessionId) => {
  const payload = await apiFetch(`/api/chat/sessions/${sessionId}`);
  const session = payload.session;
  if (!session) return;
  state.currentSessionId = session.id;
  if (elements.chatSessionId) elements.chatSessionId.value = session.id;
  if (elements.currentSessionBadge) elements.currentSessionBadge.textContent = `セッションID: ${session.id}`;
  renderChatMessages(session.messages || []);
  renderChatSessions();
};

const ensureChatReady = async () => {
  if (!state.user) return;
  await loadSessions();
  if (state.currentSessionId) {
    await loadSessionMessages(state.currentSessionId);
  }
};

const handleLogin = async (event) => {
  event.preventDefault();
  clearStatus();
  const username = elements.loginUsername?.value.trim() || '';
  const password = elements.loginPassword?.value || '';
  if (!username || !password) {
    showStatus('ユーザー名とパスワードを入力してください。', 'warning');
    return;
  }

  try {
    const payload = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    state.user = payload.user;
    await bootstrapAppData();
    renderApp();
  } catch (error) {
    showStatus(error.message || 'ログインに失敗しました。', 'danger');
  }
};

const handleLogout = async () => {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } catch (error) {
    showStatus(error.message || 'ログアウトに失敗しました。', 'warning');
  }
  setLoggedOut();
};

const handleGenerate = async (event) => {
  event.preventDefault();
  if (!elements.generateForm) return;
  toggleGenerationLoading(true);

  const modeId = elements.generationMode?.value || 'rough_with_instructions';
  const formData = new FormData(elements.generateForm);
  formData.set('mode', modeId);

  try {
    const payload = await apiFetch('/api/generations', {
      method: 'POST',
      body: formData,
      headers: {},
    });
    state.lastResult = payload.assets?.[0] || null;
    renderResult(state.lastResult);
    showStatus('生成が完了しました。', 'success');
  } catch (error) {
    showStatus(error.message || '生成に失敗しました。', 'danger');
  } finally {
    toggleGenerationLoading(false);
  }
};

const handlePresetSave = async (event) => {
  event.preventDefault();
  const payload = buildPresetPayload();
  if (!payload.name) {
    showStatus('プリセット名を入力してください。', 'warning');
    return;
  }

  try {
    const response = await apiFetch('/api/presets', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    state.presets.unshift(response.preset);
    renderPresets();
    if (elements.presetName) elements.presetName.value = '';
    showStatus('プリセットを保存しました。', 'success');
  } catch (error) {
    showStatus(error.message || 'プリセットの保存に失敗しました。', 'danger');
  }
};

const handlePresetDelete = async () => {
  const preset = findPreset();
  if (!preset) return;
  try {
    const modeId = elements.generationMode?.value || 'rough_with_instructions';
    await apiFetch(`/api/presets/${preset.id}?mode=${encodeURIComponent(modeId)}`, { method: 'DELETE' });
    state.presets = state.presets.filter((item) => item.id !== preset.id);
    renderPresets();
    showStatus('プリセットを削除しました。', 'info');
  } catch (error) {
    showStatus(error.message || 'プリセットの削除に失敗しました。', 'danger');
  }
};

const changeOwnPassword = async ({
  currentPassword,
  newPassword,
  confirmPassword,
  formElement,
  successMessage,
}) => {
  if (!currentPassword || !newPassword || !confirmPassword) {
    showStatus('現在のパスワードと新しいパスワードを入力してください。', 'warning');
    return;
  }
  if (newPassword !== confirmPassword) {
    showStatus('新しいパスワード（確認）が一致しません。', 'warning');
    return;
  }

  try {
    await apiFetch('/api/users/me/password', {
      method: 'PATCH',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    if (formElement) formElement.reset();
    showStatus(successMessage, 'success');
  } catch (error) {
    showStatus(error.message || 'パスワード変更に失敗しました。', 'danger');
  }
};

const handleAccountPasswordChange = async (event) => {
  event.preventDefault();
  await changeOwnPassword({
    currentPassword: elements.accountCurrentPassword?.value || '',
    newPassword: elements.accountNewPassword?.value || '',
    confirmPassword: elements.accountNewPasswordConfirm?.value || '',
    formElement: elements.accountPasswordForm,
    successMessage: 'パスワードを変更しました。',
  });
};

const handleAdminSelfPasswordChange = async (event) => {
  event.preventDefault();
  await changeOwnPassword({
    currentPassword: elements.adminSelfCurrentPassword?.value || '',
    newPassword: elements.adminSelfNewPassword?.value || '',
    confirmPassword: elements.adminSelfNewPasswordConfirm?.value || '',
    formElement: elements.adminSelfPasswordForm,
    successMessage: '管理者パスワードを変更しました。',
  });
};

const handleSignup = async (event) => {
  event.preventDefault();
  if (!state.user?.is_admin) {
    showStatus('管理者のみが新規登録できます。', 'warning');
    return;
  }

  const payload = {
    username: elements.signupUsername?.value.trim() || '',
    email: elements.signupEmail?.value.trim() || '',
    password: elements.signupPassword?.value || '',
  };

  if (!payload.username || !payload.email || !payload.password) {
    showStatus('すべての項目を入力してください。', 'warning');
    return;
  }

  try {
    await apiFetch('/api/admin/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    showStatus('ユーザーを作成しました。', 'success');
    if (elements.signupForm) elements.signupForm.reset();
    await loadAdminUsers();
  } catch (error) {
    showStatus(error.message || 'ユーザー作成に失敗しました。', 'danger');
  }
};

const handleNewSession = async () => {
  try {
    const payload = await apiFetch('/api/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    const session = payload.session;
    state.sessions.unshift(session);
    state.currentSessionId = session.id;
    renderChatSessions();
    await loadSessionMessages(session.id);
  } catch (error) {
    showStatus(error.message || 'セッションの作成に失敗しました。', 'danger');
  }
};

const handleChatSubmit = async (event) => {
  event.preventDefault();
  if (!state.currentSessionId) {
    showStatus('チャットセッションを選択してください。', 'warning');
    return;
  }

  const rawMessage = elements.chatMessage?.value || '';
  const message = rawMessage.trim();
  const hasImages = (elements.chatImages?.files?.length || 0) > 0;
  if (!message && !hasImages) {
    showStatus('メッセージまたは画像を入力してください。', 'warning');
    return;
  }

  const selectedMode = elements.chatModeSelect?.value || 'text_chat';
  if (elements.chatStatus) elements.chatStatus.textContent = '送信中...';
  try {
    const formData = new FormData(elements.chatForm);
    formData.set('message', message);
    await apiFetch(`/api/chat/sessions/${state.currentSessionId}/messages`, {
      method: 'POST',
      body: formData,
      headers: {},
    });
    elements.chatForm.reset();
    if (elements.chatModeSelect) {
      elements.chatModeSelect.value = selectedMode;
    }
    toggleChatExtras(selectedMode);
    await loadSessions();
    await loadSessionMessages(state.currentSessionId);
    if (elements.chatStatus) elements.chatStatus.textContent = '';
  } catch (error) {
    if (elements.chatStatus) {
      elements.chatStatus.textContent = error.message || '送信に失敗しました。';
    }
  }
};

const bindEvents = () => {
  if (elements.loginForm) elements.loginForm.addEventListener('submit', handleLogin);
  if (elements.logoutButton) elements.logoutButton.addEventListener('click', handleLogout);

  if (elements.navViews) {
    elements.navViews.querySelectorAll('button[data-view]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const viewName = btn.dataset.view || 'generate';
        setView(viewName);
        window.location.hash = viewName;
      });
    });
  }

  if (elements.generationMode) {
    elements.generationMode.addEventListener('change', async () => {
      updateModePanels(elements.generationMode.value);
      await loadPresets(elements.generationMode.value);
    });
  }

  if (elements.generateForm) elements.generateForm.addEventListener('submit', handleGenerate);
  if (elements.applyPreset) elements.applyPreset.addEventListener('click', applyPreset);
  if (elements.deletePreset) elements.deletePreset.addEventListener('click', handlePresetDelete);
  if (elements.presetForm) elements.presetForm.addEventListener('submit', handlePresetSave);
  if (elements.newSessionButton) elements.newSessionButton.addEventListener('click', handleNewSession);

  if (elements.chatSessionList) {
    elements.chatSessionList.addEventListener('click', async (event) => {
      const target = event.target.closest('[data-session-id]');
      if (!target) return;
      const sessionId = Number(target.dataset.sessionId);
      if (!sessionId) return;
      await loadSessionMessages(sessionId);
    });
  }

  if (elements.chatModeSelect) {
    elements.chatModeSelect.addEventListener('change', () => {
      toggleChatExtras(elements.chatModeSelect.value);
    });
  }

  if (elements.chatForm) elements.chatForm.addEventListener('submit', handleChatSubmit);
  if (elements.accountPasswordForm) elements.accountPasswordForm.addEventListener('submit', handleAccountPasswordChange);
  if (elements.signupForm) elements.signupForm.addEventListener('submit', handleSignup);
  if (elements.adminSelfPasswordForm) {
    elements.adminSelfPasswordForm.addEventListener('submit', handleAdminSelfPasswordChange);
  }
  if (elements.adminRefreshButton) {
    elements.adminRefreshButton.addEventListener('click', loadAdminUsers);
  }

  if (elements.adminUserTableBody) {
    elements.adminUserTableBody.addEventListener('click', async (event) => {
      const target = event.target.closest('button[data-action]');
      if (!target) return;
      const userId = Number(target.dataset.userId);
      if (!userId) return;
      const action = target.dataset.action;

      if (action === 'toggle') {
        try {
          const user = state.adminUsers.find((item) => item.id === userId);
          const nextActive = user ? !user.is_active : true;
          await apiFetch(`/api/admin/users/${userId}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ is_active: nextActive }),
          });
          await loadAdminUsers();
          showStatus('ユーザー状態を更新しました。', 'success');
        } catch (error) {
          showStatus(error.message || '状態更新に失敗しました。', 'danger');
        }
      }

      if (action === 'reset') {
        const input = elements.adminUserTableBody.querySelector(`[data-password-input="${userId}"]`);
        const newPassword = input?.value || '';
        if (!newPassword) {
          showStatus('新しいパスワードを入力してください。', 'warning');
          return;
        }
        try {
          await apiFetch(`/api/admin/users/${userId}/password`, {
            method: 'PATCH',
            body: JSON.stringify({ password: newPassword }),
          });
          if (input) input.value = '';
          showStatus('パスワードを再設定しました。', 'success');
        } catch (error) {
          showStatus(error.message || 'パスワード再設定に失敗しました。', 'danger');
        }
      }

      if (action === 'promote') {
        try {
          await apiFetch(`/api/admin/users/${userId}/role`, {
            method: 'PATCH',
            body: JSON.stringify({ role: 'admin' }),
          });
          await loadAdminUsers();
          showStatus('admin権限を付与しました。', 'success');
        } catch (error) {
          showStatus(error.message || 'admin権限の付与に失敗しました。', 'danger');
        }
      }
    });
  }

  window.addEventListener('hashchange', () => {
    const view = window.location.hash.replace('#', '');
    if (view === 'chat' || view === 'generate' || view === 'admin' || view === 'account') {
      setView(view);
    }
  });
};

const bootstrapAppData = async () => {
  const [modesPayload, optionsPayload] = await Promise.all([
    apiFetch('/api/modes'),
    apiFetch('/api/options'),
  ]);

  state.modes = modesPayload.modes || [];
  state.options = optionsPayload;
  const chatMode = state.modes.find((mode) => mode.id === 'chat_mode');
  state.chatEnabled = Boolean(chatMode?.enabled);
  if (state.chatEnabled) {
    const chatModesPayload = await apiFetch('/api/chat/modes');
    state.chatModes = chatModesPayload.modes || [];
  } else {
    state.chatModes = [];
  }

  populateModes();
  populateOptions();
  populateChatModes();

  const defaultMode = state.modes.find((mode) => mode.id === 'rough_with_instructions')?.id || state.modes[0]?.id;
  if (elements.generationMode && defaultMode) {
    elements.generationMode.value = defaultMode;
    updateModePanels(defaultMode);
  }

  if (elements.chatModeSelect && state.chatEnabled) {
    elements.chatModeSelect.value = state.chatModes[0]?.id || 'text_chat';
    toggleChatExtras(elements.chatModeSelect.value);
  }

  if (defaultMode) {
    await loadPresets(defaultMode);
  }
  renderResult(state.lastResult);

  const initialView = window.location.hash.replace('#', '') || 'generate';
  if (initialView === 'chat' || initialView === 'generate' || initialView === 'admin' || initialView === 'account') {
    setView(initialView);
  }
};

const initMaskEditor = () => {
  const modalEl = document.getElementById('maskEditorModal');
  const openButton = document.getElementById('openMaskEditorButton');
  const baseInput = document.getElementById('editBaseInput');
  const maskInput = document.getElementById('editMaskInput');
  const editMaskData = document.getElementById('editMaskData');
  const editBaseData = document.getElementById('editBaseData');
  const maskPreview = document.getElementById('editMaskPreviewImage');
  const editModeSelect = document.getElementById('editModeSelect');
  const baseCanvas = document.getElementById('maskEditorBaseCanvas');
  const maskCanvas = document.getElementById('maskEditorMaskCanvas');
  const brushSizeInput = document.getElementById('maskBrushSize');
  const eraserToggle = document.getElementById('maskEraserToggle');
  const resetButton = document.getElementById('maskResetButton');
  const applyButton = document.getElementById('maskApplyButton');

  if (!modalEl || !baseCanvas || !maskCanvas) return;

  const modal = window.bootstrap ? window.bootstrap.Modal.getOrCreateInstance(modalEl) : null;
  let baseImage = null;
  let isDrawing = false;
  let isErasing = false;

  const loadImageFromFile = (file) =>
    new Promise((resolve, reject) => {
      if (!file) return reject(new Error('missing file'));
      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = event.target.result;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const renderCanvases = () => {
    if (!baseImage) return;
    baseCanvas.width = baseImage.width;
    baseCanvas.height = baseImage.height;
    maskCanvas.width = baseImage.width;
    maskCanvas.height = baseImage.height;

    const baseCtx = baseCanvas.getContext('2d');
    const maskCtx = maskCanvas.getContext('2d');
    if (!baseCtx || !maskCtx) return;

    baseCtx.clearRect(0, 0, baseCanvas.width, baseCanvas.height);
    baseCtx.drawImage(baseImage, 0, 0);

    maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
  };

  const drawAtEvent = (event) => {
    const rect = maskCanvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * maskCanvas.width;
    const y = ((event.clientY - rect.top) / rect.height) * maskCanvas.height;
    const ctx = maskCanvas.getContext('2d');
    if (!ctx) return;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = brushSizeInput ? Number(brushSizeInput.value || 24) : 24;
    ctx.globalCompositeOperation = isErasing ? 'destination-out' : 'source-over';
    ctx.strokeStyle = 'rgba(255, 0, 0, 0.9)';
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 0.5, y + 0.5);
    ctx.stroke();
  };

  const startDraw = (event) => {
    isDrawing = true;
    drawAtEvent(event);
  };

  const moveDraw = (event) => {
    if (!isDrawing) return;
    drawAtEvent(event);
  };

  const stopDraw = () => {
    isDrawing = false;
  };

  maskCanvas.style.touchAction = 'none';
  maskCanvas.addEventListener('pointerdown', startDraw);
  maskCanvas.addEventListener('pointermove', moveDraw);
  maskCanvas.addEventListener('pointerup', stopDraw);
  maskCanvas.addEventListener('pointerleave', stopDraw);

  if (eraserToggle) {
    eraserToggle.addEventListener('click', () => {
      isErasing = !isErasing;
      eraserToggle.classList.toggle('active', isErasing);
    });
  }

  if (resetButton) {
    resetButton.addEventListener('click', () => {
      renderCanvases();
    });
  }

  const openEditor = () => {
    if (!baseImage) {
      showStatus('編集元画像を選択してください。', 'warning');
      return;
    }
    renderCanvases();
    if (modal) modal.show();
  };

  if (openButton) {
    openButton.addEventListener('click', openEditor);
  }

  if (baseInput) {
    baseInput.addEventListener('change', (event) => {
      const [file] = event.target.files || [];
      if (!file) return;
      if (editBaseData) editBaseData.value = '';
      if (editMaskData) editMaskData.value = '';
      if (maskPreview) maskPreview.classList.add('d-none');
      loadImageFromFile(file)
        .then((img) => {
          baseImage = img;
        })
        .catch(() => {
          showStatus('画像の読み込みに失敗しました。', 'danger');
        });
    });
  }

  if (maskInput) {
    maskInput.addEventListener('change', () => {
      if (editMaskData) editMaskData.value = '';
      if (maskPreview) maskPreview.classList.add('d-none');
    });
  }

  if (applyButton) {
    applyButton.addEventListener('click', () => {
      if (!baseImage) return;
      if (editMaskData) editMaskData.value = maskCanvas.toDataURL('image/png');
      if (editBaseData) editBaseData.value = baseCanvas.toDataURL('image/png');
      if (maskPreview) {
        maskPreview.src = maskCanvas.toDataURL('image/png');
        maskPreview.classList.remove('d-none');
      }
      if (modal) modal.hide();
    });
  }

  if (editModeSelect) {
    editModeSelect.addEventListener('change', () => {
      if (editMaskData) editMaskData.value = '';
      if (maskPreview) maskPreview.classList.add('d-none');
    });
  }
};

const initApp = async () => {
  cacheElements();
  initRoughUploadPreviews();
  initResultImageViewer();
  bindEvents();
  initMaskEditor();

  try {
    const payload = await apiFetch('/api/me');
    if (payload.authenticated) {
      state.user = payload.user;
      await bootstrapAppData();
      renderApp();
    } else {
      renderLogin();
    }
  } catch (error) {
    renderLogin();
  }
};

document.addEventListener('DOMContentLoaded', initApp);
