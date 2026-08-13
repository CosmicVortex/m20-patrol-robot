/**
 * ViewRouter - Simple SPA router for M20 Pro patrol system
 * Manages view switching and navigation state
 */
class ViewRouter {
  constructor(stateManager) {
    this.state = stateManager;
    this._views = new Map();
    this._currentView = 'dashboard';
  }
  
  /**
   * Register a view component
   * @param {string} name - View name (matches URL hash or state)
   * @param {object} component - Component object with init(), destroy(), render()
   */
  register(name, component) {
    this._views.set(name, component);
  }
  
  /**
   * Navigate to a view
   * @param {string} name - View name
   * @param {object} params - Optional parameters
   */
  async navigate(name, params = {}) {
    if (!this._views.has(name)) {
      name = 'dashboard';
    }
    // Hide all view containers
    document.querySelectorAll('.view-container').forEach(el => {
      el.classList.add('hidden');
    });
    
    // Unload current view
    if (this._currentView && this._views.has(this._currentView)) {
      const prev = this._views.get(this._currentView);
      if (prev.destroy) {
        try { prev.destroy(); } catch (e) { console.error('View destroy error:', e); }
      }
    }
    
    // Load new view
    this._currentView = name;
    this.state.set('currentView', name);
    
    // Update nav active state
    this._updateNavActive(name);
    
    // Show the target view container
    const targetView = document.getElementById(`view-${name}`);
    if (targetView) {
      targetView.classList.remove('hidden');
    }
    
    // Render new view
    const component = this._views.get(name);
    if (component) {
      try {
        await component.init?.(params);
        component.render?.();
      } catch (e) {
        console.error(`View ${name} render error:`, e);
      }
    } else {
      console.warn(`View ${name} not registered`);
    }
  }
  
  /**
   * Update navigation active state
   */
  _updateNavActive(viewName) {
    document.querySelectorAll('.nav button').forEach(btn => {
      const isActive = btn.dataset.view === viewName;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-current', isActive ? 'page' : 'false');
    });
  }
  
  /**
   * Get current view name
   */
  getCurrentView() {
    return this._currentView;
  }
  
  /**
   * Handle browser back/forward
   */
  handlePopState() {
    const hash = location.hash.slice(1) || 'dashboard';
    this.navigate(hash);
  }
  
  /**
   * Initialize routing
   */
  init() {
    if (this._initialized) return;
    this._initialized = true;
    window.addEventListener('popstate', () => this.handlePopState());
    
    // Handle nav clicks
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.nav button[data-view]');
      if (btn) {
        e.preventDefault();
        const viewName = btn.dataset.view;
        history.pushState(null, '', `#${viewName}`);
        this.navigate(viewName);
      }
    });
    
    // Initial navigation
    const initialView = location.hash.slice(1) || 'dashboard';
    this.navigate(initialView);
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ViewRouter };
}
