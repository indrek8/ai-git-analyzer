class GitAnalyticsApp {
    constructor() {
        this.apiBase = '/api';
        this.token = localStorage.getItem('token');
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkAuth();
    }

    setupEventListeners() {
        // Login form
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        // Navigation
        document.querySelectorAll('.nav-link[data-page]').forEach(link => {
            link.addEventListener('click', (e) => this.handleNavigation(e));
        });

        // Logout
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // Repository management
        const addRepoBtn = document.getElementById('add-repo-btn');
        const cancelAddRepo = document.getElementById('cancel-add-repo');
        const repoForm = document.getElementById('repository-form');

        if (addRepoBtn) {
            addRepoBtn.addEventListener('click', () => this.showAddRepoForm());
        }

        if (cancelAddRepo) {
            cancelAddRepo.addEventListener('click', () => this.hideAddRepoForm());
        }

        if (repoForm) {
            repoForm.addEventListener('submit', (e) => this.handleAddRepository(e));
        }

        // Settings form
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => this.handleSettings(e));
        }
    }

    checkAuth() {
        if (this.token) {
            this.showPage('dashboard');
            this.loadDashboardData();
        } else {
            this.showPage('login');
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const username = formData.get('username');
        const password = formData.get('password');

        try {
            const response = await fetch(`${this.apiBase}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
            });

            if (response.ok) {
                const data = await response.json();
                this.token = data.access_token;
                localStorage.setItem('token', this.token);
                this.showPage('dashboard');
                this.loadDashboardData();
                document.getElementById('login-error').textContent = '';
            } else {
                document.getElementById('login-error').textContent = 'Invalid credentials';
            }
        } catch (error) {
            console.error('Login error:', error);
            document.getElementById('login-error').textContent = 'Login failed. Please try again.';
        }
    }

    handleLogout() {
        this.token = null;
        localStorage.removeItem('token');
        this.showPage('login');
    }

    handleNavigation(e) {
        e.preventDefault();
        const page = e.target.dataset.page;
        this.showPage(page);

        // Load page-specific data
        switch (page) {
            case 'dashboard':
                this.loadDashboardData();
                break;
            case 'repositories':
                this.loadRepositories();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
        }
    }

    showPage(pageId) {
        // Hide all pages
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });

        // Show target page
        const targetPage = document.getElementById(`${pageId}-page`);
        if (targetPage) {
            targetPage.classList.add('active');
        }

        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });

        const activeLink = document.querySelector(`[data-page="${pageId}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }

        // Show/hide navigation based on login status
        const navbar = document.querySelector('.navbar');
        if (pageId === 'login') {
            navbar.style.display = 'none';
        } else {
            navbar.style.display = 'block';
        }
    }

    async apiCall(endpoint, options = {}) {
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...(this.token && { 'Authorization': `Bearer ${this.token}` })
            },
            ...options
        };

        const response = await fetch(`${this.apiBase}${endpoint}`, config);
        
        if (response.status === 401) {
            this.handleLogout();
            return null;
        }

        return response.json();
    }

    async loadDashboardData() {
        try {
            // Load basic stats (placeholder data for now)
            document.getElementById('total-repos').textContent = '0';
            document.getElementById('total-commits').textContent = '0';
            document.getElementById('active-developers').textContent = '0';
            document.getElementById('effort-score').textContent = '0';
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    async loadRepositories() {
        try {
            const repositories = await this.apiCall('/repositories');
            this.renderRepositories(repositories?.repositories || []);
        } catch (error) {
            console.error('Failed to load repositories:', error);
        }
    }

    renderRepositories(repositories) {
        const container = document.getElementById('repository-list');
        if (!container) return;

        if (repositories.length === 0) {
            container.innerHTML = '<p>No repositories added yet. Click "Add Repository" to get started.</p>';
            return;
        }

        container.innerHTML = repositories.map(repo => `
            <div class="repository-item">
                <div class="repository-info">
                    <h3>${repo.name}</h3>
                    <p>${repo.url}</p>
                    <p>Provider: ${repo.provider} | Status: ${repo.sync_status}</p>
                </div>
                <div class="repository-actions">
                    <button class="btn btn-primary" onclick="app.syncRepository(${repo.id})">Sync</button>
                    <button class="btn btn-secondary" onclick="app.removeRepository(${repo.id})">Remove</button>
                </div>
            </div>
        `).join('');
    }

    showAddRepoForm() {
        document.getElementById('add-repo-form').style.display = 'block';
    }

    hideAddRepoForm() {
        document.getElementById('add-repo-form').style.display = 'none';
        document.getElementById('repository-form').reset();
    }

    async handleAddRepository(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const repoUrl = formData.get('repo-url');
        const provider = formData.get('provider');

        try {
            const result = await this.apiCall('/repositories', {
                method: 'POST',
                body: JSON.stringify({
                    repo_url: repoUrl,
                    provider: provider
                })
            });

            if (result) {
                this.hideAddRepoForm();
                this.loadRepositories();
            }
        } catch (error) {
            console.error('Failed to add repository:', error);
        }
    }

    async syncRepository(repoId) {
        try {
            await this.apiCall(`/repositories/${repoId}/sync`, {
                method: 'POST'
            });
            this.loadRepositories();
        } catch (error) {
            console.error('Failed to sync repository:', error);
        }
    }

    async removeRepository(repoId) {
        if (confirm('Are you sure you want to remove this repository?')) {
            try {
                await this.apiCall(`/repositories/${repoId}`, {
                    method: 'DELETE'
                });
                this.loadRepositories();
            } catch (error) {
                console.error('Failed to remove repository:', error);
            }
        }
    }

    async loadAnalytics() {
        try {
            const analytics = await this.apiCall('/analytics/effort');
            // TODO: Render analytics charts
            console.log('Analytics data:', analytics);
        } catch (error) {
            console.error('Failed to load analytics:', error);
        }
    }

    async handleSettings(e) {
        e.preventDefault();
        // TODO: Implement settings save
        alert('Settings saved successfully!');
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new GitAnalyticsApp();
});