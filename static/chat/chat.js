document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.querySelector('#chat-box');
    const messageForm = document.querySelector('#message-form');
    const messageInput = document.querySelector('#message-input');
    const sendButton = messageForm ? messageForm.querySelector('button[type="submit"]') : null;

    if (!chatBox || !messageForm || !messageInput || !sendButton) {
        console.error('Missing chat elements:', { chatBox, messageForm, messageInput, sendButton });
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
            chatBox.innerHTML = '';
            messages.forEach(msg => {
                const div = document.createElement('div');
                div.className = `mb-2 ${msg.sender_id == userId ? 'text-end' : 'text-start'}`;
                div.innerHTML = `
                    <small class="text-muted">${msg.sender_name} - ${msg.timestamp}</small>
                    <div class="p-2 rounded ${msg.sender_id == userId ? 'bg-primary text-white' : 'bg-light'}">
                        ${msg.content}
                    </div>
                `;
                chatBox.appendChild(div);
            });
            chatBox.scrollTop = chatBox.scrollHeight;
        } catch (error) {
            console.error('Error fetching messages:', error);
            chatBox.innerHTML += `<div class="text-danger text-center">Failed to load messages: ${error.message}</div>`;
        }
    };

    // Send message
    messageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = messageInput.value.trim();
        if (!content) return;

        sendButton.disabled = true;
        try {
            const response = await fetch(`/chat/${chatId}/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `content=${encodeURIComponent(content)}`
            });
            const result = await response.json();
            if (result.success) {
                messageInput.value = '';
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

    // Initial fetch and polling every 5 seconds
    fetchMessages();
    setInterval(fetchMessages, 5000);
});