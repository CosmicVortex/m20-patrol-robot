/**
 * WebSocketService - Manages WebSocket connections for real-time data
 */
class WebSocketService {
  constructor(stateManager) {
    this.state = stateManager;
    this._wsVideo = null;
    this._wsNav = null;
    this._reconnectTimer = null;
    this._urlBase = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`;
  }
  
  /**
   * Get WebSocket URL
   */
  _getWsUrl(path) {
    return `${this._urlBase}${path}`;
  }
  
  /**
   * Connect to video WebSocket
   */
  connectVideo() {
    if (this._wsVideo && this._wsVideo.readyState === WebSocket.OPEN) return;
    
    try {
      this._wsVideo = new WebSocket(this._getWsUrl('/ws/video'));
      
      this._wsVideo.onopen = () => {
        console.log('[WS] Video connected');
        this.state.set('video.wsConnected', true);
      };
      
      this._wsVideo.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this._handleVideoMessage(data);
        } catch (e) {
          console.error('[WS] Video message parse error:', e);
        }
      };
      
      this._wsVideo.onclose = () => {
        console.log('[WS] Video disconnected');
        this.state.set('video.wsConnected', false);
        this._wsVideo = null;
        this._scheduleReconnect();
      };
      
      this._wsVideo.onerror = () => {
        console.error('[WS] Video error');
      };
    } catch (e) {
      console.error('[WS] Video init error:', e);
    }
  }
  
  /**
   * Connect to navigation WebSocket
   */
  connectNav() {
    if (this._wsNav && this._wsNav.readyState === WebSocket.OPEN) return;
    
    try {
      this._wsNav = new WebSocket(this._getWsUrl('/ws/navigation'));
      
      this._wsNav.onopen = () => {
        console.log('[WS] Navigation connected');
        this.state.set('nav.wsConnected', true);
      };
      
      this._wsNav.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this._handleNavMessage(data);
        } catch (e) {
          console.error('[WS] Nav message parse error:', e);
        }
      };
      
      this._wsNav.onclose = () => {
        console.log('[WS] Navigation disconnected');
        this.state.set('nav.wsConnected', false);
        this._wsNav = null;
        this._scheduleReconnect();
      };
      
      this._wsNav.onerror = () => {
        console.error('[WS] Nav error');
      };
    } catch (e) {
      console.error('[WS] Nav init error:', e);
    }
  }
  
  /**
   * Handle video WebSocket messages
   */
  _handleVideoMessage(data) {
    switch (data.type) {
      case 'video_states':
        this.state.updateVideo({ sources: data.data, status: 'VIDEO_IO_ENABLED' });
        break;
      case 'frame':
        // Handle video frame (base64 or blob URL)
        this._handleVideoFrame(data);
        break;
    }
  }
  
  /**
   * Handle video frame data
   */
  _handleVideoFrame(data) {
    // Implementation depends on frame format
    // Could be base64 image data or streaming URL
    console.log('[WS] Video frame received:', data);
  }
  
  /**
   * Handle navigation WebSocket messages
   */
  _handleNavMessage(data) {
    switch (data.type) {
      case 'error':
        console.error('[WS] Nav error:', data.message);
        break;
      case 'status':
        this.state.updateNavigation(data.data);
        break;
    }
  }
  
  /**
   * Send video WebSocket message
   */
  sendVideo(action, params = {}) {
    if (!this._wsVideo || this._wsVideo.readyState !== WebSocket.OPEN) return null;
    this._wsVideo.send(JSON.stringify({ action, ...params }));
    return true;
  }
  
  /**
   * Send navigation WebSocket message
   */
  sendNav(action, params = {}) {
    if (!this._wsNav || this._wsNav.readyState !== WebSocket.OPEN) return null;
    this._wsNav.send(JSON.stringify({ action, ...params }));
    return true;
  }
  
  /**
   * Schedule reconnection
   */
  _scheduleReconnect() {
    if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
    this._reconnectTimer = setTimeout(() => {
      this.connectVideo();
      this.connectNav();
    }, 3000);
  }
  
  /**
   * Disconnect all
   */
  disconnect() {
    if (this._wsVideo) {
      this._wsVideo.close();
      this._wsVideo = null;
    }
    if (this._wsNav) {
      this._wsNav.close();
      this._wsNav = null;
    }
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
    }
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { WebSocketService };
}
