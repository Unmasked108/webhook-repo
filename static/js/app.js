class WebhookEventManager {
    constructor() {
        this.events = [];
        this.isLoading = false;
        this.lastUpdateTime = null;
        this.refreshInterval = 15000; // 15 seconds
        this.retryCount = 0;
        this.maxRetries = 3;
        
        this.init();
    }
    
    init() {
        this.loadEvents();
        this.startAutoRefresh();
        this.updateStatus('connecting');
    }
    
    async loadEvents() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const response = await fetch('/api/events');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const newEvents = await response.json();
            
            // Check if we have new events
            const hasNewEvents = this.events.length === 0 || 
                                newEvents.length > this.events.length ||
                                (newEvents.length > 0 && this.events.length > 0 && 
                                 newEvents[0].id !== this.events[0].id);
            
            this.events = newEvents;
            this.renderEvents(hasNewEvents);
            this.updateStatus('connected');
            this.updateLastUpdateTime();
            this.retryCount = 0;
            
        } catch (error) {
            console.error('Error loading events:', error);
            this.updateStatus('error');
            this.retryCount++;
            
            if (this.retryCount < this.maxRetries) {
                setTimeout(() => this.loadEvents(), 5000);
            }
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    renderEvents(hasNewEvents = false) {
        const eventsContainer = document.getElementById('events-list');
        const noEventsContainer = document.getElementById('no-events');
        
        if (this.events.length === 0) {
            eventsContainer.innerHTML = '';
            noEventsContainer.style.display = 'block';
            return;
        }
        
        noEventsContainer.style.display = 'none';
        
        const eventsHTML = this.events.map((event, index) => {
            const eventTime = new Date(event.timestamp);
            const formattedTime = this.formatEventTime(eventTime);
            const isNewEvent = hasNewEvents && index < 3; // Mark first 3 as new if there are new events
            
            return `
                <div class="event-item ${event.event_type} ${isNewEvent ? 'new' : ''}" data-event-id="${event.id}">
                    <div class="event-header">
                        <span class="event-type ${event.event_type}">${event.event_type.replace('_', ' ')}</span>
                        <span class="event-time">${formattedTime}</span>
                    </div>
                    <div class="event-content">
                        "<span class="event-author">${this.escapeHtml(event.author)}</span>" ${this.escapeHtml(event.details)}
                    </div>
                    <div class="event-repo">Repository: ${this.escapeHtml(event.repository)}</div>
                </div>
            `;
        }).join('');
        
        eventsContainer.innerHTML = eventsHTML;
        
        // Remove 'new' class after animation
        setTimeout(() => {
            document.querySelectorAll('.event-item.new').forEach(item => {
                item.classList.remove('new');
            });
        }, 500);
    }
    
    formatEventTime(date) {
        const now = new Date();
        const diff = now - date;
        
        // If within last hour, show relative time
        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            if (minutes < 1) return 'Just now';
            return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
        }
        
        // If today, show time
        if (date.toDateString() === now.toDateString()) {
            return date.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: true 
            });
        }
        
        // If within last week, show day and time
        if (diff < 604800000) {
            return date.toLocaleDateString('en-US', { 
                weekday: 'short',
                hour: '2-digit', 
                minute: '2-digit',
                hour12: true 
            });
        }
        
        // Otherwise, show full date
        return date.toLocaleDateString('en-US', { 
            year: 'numeric',
            month: 'short', 
            day: 'numeric',
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    }
    
    updateStatus(status) {
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');
        
        statusDot.className = `status-dot ${status}`;
        
        switch (status) {
            case 'connected':
                statusText.textContent = 'Connected';
                break;
            case 'connecting':
                statusText.textContent = 'Connecting...';
                break;
            case 'error':
                statusText.textContent = 'Connection Error';
                break;
            default:
                statusText.textContent = 'Unknown';
        }
    }
    
    updateLastUpdateTime() {
        const now = new Date();
        this.lastUpdateTime = now;
        document.getElementById('last-updated').textContent = now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
    }
    
    showLoading() {
        document.getElementById('loading').style.display = 'block';
    }
    
    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    }
    
    startAutoRefresh() {
        setInterval(() => {
            this.loadEvents();
        }, this.refreshInterval);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new WebhookEventManager();
});

// Handle visibility change to refresh when tab becomes active
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        // Refresh events when tab becomes visible
        setTimeout(() => {
            if (window.webhookManager) {
                window.webhookManager.loadEvents();
            }
        }, 1000);
    }
});

// Add some debugging
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

// Make manager available globally for debugging
window.addEventListener('load', () => {
    if (!window.webhookManager) {
        window.webhookManager = new WebhookEventManager();
    }
});