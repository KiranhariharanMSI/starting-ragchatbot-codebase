// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    
    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea
    chatInput.addEventListener('input', autoResizeTextarea);
    
    
    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}

// Auto-resize textarea
function autoResizeTextarea() {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
}

// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input and provide visual feedback
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;
    chatInput.placeholder = 'Processing your message...';

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        // Special handling for insufficient credits
        if (response.status === 402) {
            let detail = 'LLM calls are failing due to insufficient credits. Please top up and try again.';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            loadingMessage.remove();
            addMessage(`⚠️ ${detail}`, 'assistant');
            return;
        }

        // Handle rate limiting
        if (response.status === 429) {
            let detail = 'Too many requests. Please wait a moment and try again.';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            loadingMessage.remove();
            addMessage(`🚦 ${detail}`, 'assistant');
            return;
        }

        // Handle authentication/authorization issues
        if (response.status === 401 || response.status === 403) {
            let detail = 'Authentication failed. Please check your API credentials.';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            loadingMessage.remove();
            addMessage(`🔒 ${detail}`, 'assistant');
            return;
        }

        // Handle server errors
        if (response.status >= 500) {
            let detail = 'Server is temporarily unavailable. Please try again in a moment.';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            loadingMessage.remove();
            addMessage(`🔧 ${detail}`, 'assistant');
            return;
        }

        if (!response.ok) {
            // Try to surface backend error detail directly
            let detail = `Request failed with status ${response.status}`;
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {
                try { 
                    const text = await response.text(); 
                    if (text) detail = text;
                } catch (_) {}
            }
            loadingMessage.remove();
            addMessage(`❌ ${detail}`, 'assistant');
            return;
        }

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Handle network and other errors
        loadingMessage.remove();
        let errorMessage = 'Connection failed. Please check your internet connection and try again.';
        
        // Check for specific error types
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage = 'Unable to connect to the server. Please check if the application is running.';
        } else if (error.name === 'AbortError') {
            errorMessage = 'Request was cancelled. Please try again.';
        } else if (error.message.includes('CSP') || error.message.includes('Content Security Policy')) {
            errorMessage = 'Security policy blocked the request. Please contact support.';
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        addMessage(`🌐 ${errorMessage}`, 'assistant');
        console.error('Chat request failed:', error);
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.placeholder = 'Type your message here...';
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sources.join(', ')}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        
        // Handle rate limiting for course stats
        if (response.status === 429) {
            console.warn('Rate limited while loading course stats');
            if (totalCourses) totalCourses.textContent = '-';
            if (courseTitles) {
                courseTitles.innerHTML = '<span class="rate-limited">Rate limited - try refreshing later</span>';
            }
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: Failed to load course stats`);
        }
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set user-friendly error messages
        if (totalCourses) {
            totalCourses.textContent = '?';
        }
        if (courseTitles) {
            let errorMsg = 'Failed to load courses';
            if (error.message.includes('fetch')) {
                errorMsg = 'Connection failed';
            } else if (error.message.includes('429')) {
                errorMsg = 'Too many requests - try refreshing';
            }
            courseTitles.innerHTML = `<span class="error">${errorMsg}</span>`;
        }
    }
}