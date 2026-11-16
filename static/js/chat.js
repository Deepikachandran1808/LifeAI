/* ========================================================
   LifeAI - AI Chatbot Interactive Engine
   ======================================================== */

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const messagesContainer = document.getElementById('chatMessages');
    const clearChatBtn = document.getElementById('clearChatBtn');

    // Scroll to bottom on initial load
    scrollToBottom();

    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = chatInput.value.trim();
            if (!message) return;

            // Append user message immediately
            appendUserMessage(message);
            chatInput.value = '';
            chatInput.focus();

            // Append typing indicator
            const typingId = showTypingIndicator();
            scrollToBottom();

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                removeTypingIndicator(typingId);

                if (data.success) {
                    appendAIMessage(data.reply);
                } else {
                    appendAIMessage("⚠️ Sorry, I encountered an issue processing that. Please try again.");
                }
            } catch (err) {
                removeTypingIndicator(typingId);
                appendAIMessage("⚠️ Network connection error. Please verify the server is running.");
            }

            scrollToBottom();
        });
    }

    // Suggestion chips
    document.querySelectorAll('.chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.getAttribute('data-prompt');
            if (chatInput && prompt) {
                chatInput.value = prompt;
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    });

    // Clear chat
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to clear your chat history?')) {
                await fetch('/api/chat/clear', { method: 'POST' });
                messagesContainer.innerHTML = '';
                appendAIMessage("Chat history cleared. How can I assist you with your day today?");
            }
        });
    }

    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'message-row user';
        row.innerHTML = `
            <div class="message-avatar user-avatar">U</div>
            <div class="message-bubble">${escapeHtml(text)}</div>
        `;
        messagesContainer.appendChild(row);
    }

    function appendAIMessage(markdownText) {
        const row = document.createElement('div');
        row.className = 'message-row assistant';
        const formatted = formatMarkdown(markdownText);
        row.innerHTML = `
            <div class="message-avatar ai-avatar">AI</div>
            <div class="message-bubble">${formatted}</div>
        `;
        messagesContainer.appendChild(row);
    }

    function showTypingIndicator() {
        const id = 'typing_' + Date.now();
        const row = document.createElement('div');
        row.id = id;
        row.className = 'message-row assistant';
        row.innerHTML = `
            <div class="message-avatar ai-avatar">AI</div>
            <div class="message-bubble" style="color: var(--text-muted); font-style: italic;">
                Thinking and analyzing your schedule...
            </div>
        `;
        messagesContainer.appendChild(row);
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    function escapeHtml(str) {
        return str.replace(/[&<>"']/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            }[m];
        });
    }

    function formatMarkdown(text) {
        // Convert basic markdown elements to HTML
        let html = escapeHtml(text);
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Bullets
        html = html.replace(/^[•\-\*]\s+(.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        // Newlines to <br>
        html = html.replace(/\n/g, '<br>');
        // Links like [text](url)
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:var(--primary);text-decoration:underline;">$1</a>');
        // Code spans
        html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1);padding:2px 6px;border-radius:4px;font-family:monospace;">$1</code>');
        return html;
    }
});
