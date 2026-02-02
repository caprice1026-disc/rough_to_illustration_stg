const buildMessageElement = (message) => {
  const wrapper = document.createElement('div');
  wrapper.className = `chat-message ${message.role === 'user' ? 'is-user' : 'is-assistant'}`;

  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';

  const meta = document.createElement('div');
  meta.className = 'chat-meta';
  const role = document.createElement('span');
  role.className = 'chat-role';
  role.textContent = message.role === 'user' ? 'You' : 'Assistant';
  meta.appendChild(role);
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
      img.alt = 'attachment';
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
  return wrapper;
};

const buildUserAttachments = (files) => {
  if (!files || files.length === 0) return [];
  return Array.from(files).map((file) => ({
    kind: 'image',
    url: URL.createObjectURL(file),
  }));
};

const initChatForm = () => {
  const form = document.getElementById('chatForm');
  const messages = document.getElementById('chatMessages');
  const submitButton = document.getElementById('chatSubmit');
  const status = document.getElementById('chatStatus');
  const fileInput = document.getElementById('chatImages');
  if (!form || !messages || !submitButton) return;

  const endpoint = form.dataset.endpoint || '/chat/messages';

  const scrollToBottom = () => {
    messages.scrollTop = messages.scrollHeight;
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const messageText = formData.get('message') || '';
    const files = fileInput ? fileInput.files : null;

    if (!messageText && (!files || files.length === 0)) {
      if (status) status.textContent = 'Please enter a message or attach images.';
      return;
    }

    submitButton.disabled = true;
    if (status) status.textContent = 'Sending...';

    const userMessage = {
      role: 'user',
      text: messageText,
      attachments: buildUserAttachments(files),
    };

    const emptyState = messages.querySelector('.empty-chat');
    if (emptyState) emptyState.remove();
    const userElement = buildMessageElement(userMessage);
    messages.appendChild(userElement);
    scrollToBottom();

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to send message.');
      }
      if (payload.assistant) {
        messages.appendChild(buildMessageElement(payload.assistant));
      }
      form.reset();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message.';
      if (status) status.textContent = errorMessage;
      if (userElement) userElement.remove();
    } finally {
      submitButton.disabled = false;
      if (status && status.textContent === 'Sending...') status.textContent = '';
      scrollToBottom();
    }
  });
};

const bootstrapChatPage = () => {
  initChatForm();
};

document.addEventListener('DOMContentLoaded', bootstrapChatPage);
