document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.querySelector('#chat-messages');
    const messageForm = document.querySelector('#chat-form');
    const messageInput = document.querySelector('#content');
    const fileInput = document.querySelector('#fileInput');
    const typingIndicator = document.querySelector('#typing-indicator');
    const sendButton = messageForm ? messageForm.querySelector('button[type="submit"]') : null;

    if (!chatBox || !messageForm || !messageInput || !fileInput || !typingIndicator || !sendButton) {
        console.error('Missing chat elements:', { chatBox, messageForm, messageInput, fileInput, typingIndicator, sendButton });
        return;
    }

    const chatId = chatBox.dataset.chat;
    const userId = chatBox.dataset.user;

    // Fetch and render messages
    const fetchMessages = async () => {
        try {
            const response = await fetch(`/chat/${chatId}/messages`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${await response.text()}`);
            }
            const messages = await response.json();
            const existingIds = new Set(Array.from(chatBox.querySelectorAll('.message')).map(m => m.dataset.messageId));
            messages.forEach(msg => {
                if (!existingIds.has(String(msg.id))) {
                    const div = document.createElement('div');
                    div.className = `message ${msg.sender_id == userId ? 'text-end' : 'text-start'} mb-3`;
                    div.dataset.messageId = msg.id;
                    div.innerHTML = `
                        <div class="d-inline-block p-2 px-3 rounded ${msg.sender_id == userId ? 'bg-primary text-white' : 'bg-light'}">
                            <p class="mb-1">${msg.content || ''}</p>
                            ${msg.attachment_url ? `
                                ${msg.attachment_url.match(/\.(png|jpg|jpeg|gif)$/) ?
                                    `<img src="/static/${msg.attachment_url}" alt="Attachment" class="img-fluid" style="max-width: 200px;">` :
                                    `<a href="/static/${msg.attachment_url}" download><i class="bi bi-file-earmark-arrow-down"></i> Download Attachment</a>`
                                }
                            ` : ''}
                            <small class="text-muted d-block">
                                ${msg.timestamp}
                                ${msg.sender_id == userId ? `<i class="bi bi-check2-all ${msg.is_read ? 'text-primary' : 'text-muted'}"></i>` : ''}
                            </small>
                        </div>
                    `;
                    chatBox.appendChild(div);
                }
            });
            chatBox.scrollTop = chatBox.scrollHeight;
        } catch (error) {
            console.error('Error fetching messages:', error);
            chatBox.innerHTML += `<div class="text-danger text-center">Failed to load messages: ${error.message}</div>`;
        }
    };

    // Check typing status
    const checkTypingStatus = async () => {
        try {
            const response = await fetch(`/chat/${chatId}/typing_status`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            typingIndicator.style.display = data.is_typing ? 'block' : 'none';
            typingIndicator.textContent = `${data.partner_name} is typing...`;
        } catch (error) {
            console.error('Error checking typing status:', error);
        }
    };

    // Send typing status
    let typingTimeout;
    const sendTypingStatus = async (typing) => {
        try {
            const response = await fetch(`/chat/${chatId}/typing`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ typing })
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Error sending typing status:', error);
        }
    };

    messageInput.addEventListener('input', () => {
        clearTimeout(typingTimeout);
        sendTypingStatus(true);
        typingTimeout = setTimeout(() => sendTypingStatus(false), 2000);
    });

    // Mark messages as read
    const markMessagesAsRead = async () => {
        try {
            const response = await fetch(`/chat/${chatId}/read`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            await fetchMessages(); // Refresh to update seen ticks
        } catch (error) {
            console.error('Error marking messages as read:', error);
        }
    };

    // Send message or attachment
    messageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = messageInput.value.trim();
        const file = fileInput.files[0];
        if (!content && !file) {
            alert('Please enter a message or select a file.');
            return;
        }

        sendButton.disabled = true;
        try {
            const formData = new FormData();
            if (content) formData.append('content', content);
            if (file) formData.append('file', file);

            const response = await fetch(`/chat/${chatId}/send`, {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (result.success) {
                messageInput.value = '';
                fileInput.value = '';
                await fetchMessages();
            } else {
                alert('Error sending message: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error sending message:', error);
            alert('Error sending message: ' + error.message);
        } finally {
            sendButton.disabled = false;
        }
    });

    // Poll for updates
    const pollChat = async () => {
        await fetchMessages();
        await checkTypingStatus();
    };

    // Initial setup
    pollChat();
    markMessagesAsRead();
    setInterval(pollChat, 3000);
    window.addEventListener('focus', markMessagesAsRead);
});