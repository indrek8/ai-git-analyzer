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

        // GitHub user management
        const addGitHubUserBtn = document.getElementById('add-github-user-btn');
        const cancelAddGitHubUser = document.getElementById('cancel-add-github-user');
        const githubUserForm = document.getElementById('github-user-form');

        if (addGitHubUserBtn) {
            addGitHubUserBtn.addEventListener('click', () => this.showAddGitHubUserForm());
        }

        if (cancelAddGitHubUser) {
            cancelAddGitHubUser.addEventListener('click', () => this.hideAddGitHubUserForm());
        }

        if (githubUserForm) {
            githubUserForm.addEventListener('submit', (e) => this.handleAddGitHubUser(e));
        }

        // GitHub organization management
        const connectGitHubOrgBtn = document.getElementById('connect-github-org-btn');
        const startOAuthBtn = document.getElementById('start-oauth-btn');
        const cancelOAuthBtn = document.getElementById('cancel-oauth-btn');

        if (connectGitHubOrgBtn) {
            connectGitHubOrgBtn.addEventListener('click', () => this.showOAuthModal());
        }

        if (startOAuthBtn) {
            startOAuthBtn.addEventListener('click', () => this.startGitHubOAuth());
        }

        if (cancelOAuthBtn) {
            cancelOAuthBtn.addEventListener('click', () => this.hideOAuthModal());
        }

        // Repository selection modal
        const closeModal = document.getElementById('close-modal');
        const selectAllRepos = document.getElementById('select-all-repos');
        const deselectAllRepos = document.getElementById('deselect-all-repos');
        const syncSelectedRepos = document.getElementById('sync-selected-repos');
        const repoSearch = document.getElementById('repo-search');
        const languageFilter = document.getElementById('language-filter');

        if (closeModal) {
            closeModal.addEventListener('click', () => this.closeRepoSelectionModal());
        }

        if (selectAllRepos) {
            selectAllRepos.addEventListener('click', () => this.selectAllRepositories());
        }

        if (deselectAllRepos) {
            deselectAllRepos.addEventListener('click', () => this.deselectAllRepositories());
        }

        if (syncSelectedRepos) {
            syncSelectedRepos.addEventListener('click', () => this.syncSelectedRepositories());
        }

        if (repoSearch) {
            repoSearch.addEventListener('input', () => this.filterRepositories());
        }

        if (languageFilter) {
            languageFilter.addEventListener('change', () => this.filterRepositories());
        }

        // Task management
        const refreshTasksBtn = document.getElementById('refresh-tasks-btn');
        const bulkSyncBtn = document.getElementById('bulk-sync-btn');

        if (refreshTasksBtn) {
            refreshTasksBtn.addEventListener('click', () => this.loadTaskData());
        }

        if (bulkSyncBtn) {
            bulkSyncBtn.addEventListener('click', () => this.startBulkSync());
        }
    }

    async checkAuth() {
        if (this.token) {
            // Verify token is still valid
            try {
                const userInfo = await this.apiCall('/auth/me');
                if (userInfo) {
                    localStorage.setItem('user', JSON.stringify(userInfo));
                    this.updateUserDisplay(userInfo);
                    this.showPage('dashboard');
                    this.loadDashboardData();
                    return;
                }
            } catch (error) {
                console.log('Token invalid, redirecting to login');
            }
        }
        
        // Token invalid or missing
        this.token = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        this.showPage('login');
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

            const data = await response.json();

            if (response.ok) {
                this.token = data.access_token;
                localStorage.setItem('token', this.token);
                
                // Load user info
                const userInfo = await this.apiCall('/auth/me');
                if (userInfo) {
                    localStorage.setItem('user', JSON.stringify(userInfo));
                    this.updateUserDisplay(userInfo);
                    this.showPage('dashboard');
                    this.loadDashboardData();
                    document.getElementById('login-error').textContent = '';
                } else {
                    document.getElementById('login-error').textContent = 'Failed to load user information';
                }
            } else {
                console.error('Login failed:', data);
                document.getElementById('login-error').textContent = data.detail || 'Invalid credentials';
            }
        } catch (error) {
            console.error('Login error:', error);
            document.getElementById('login-error').textContent = 'Login failed. Please try again.';
        }
    }

    handleLogout() {
        this.token = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
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
            case 'github':
                this.loadGitHubUsers();
                this.loadGitHubOrganizations();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
            case 'tasks':
                this.loadTaskData();
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

        try {
            const response = await fetch(`${this.apiBase}${endpoint}`, config);
            
            if (response.status === 401) {
                this.handleLogout();
                return null;
            }

            if (!response.ok) {
                console.error(`API call failed: ${response.status} ${response.statusText}`);
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('API call error:', error);
            return null;
        }
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
            container.innerHTML = '<div class="repository-item"><p>No repositories added yet. Click "Add Repository" to get started.</p></div>';
            return;
        }

        container.innerHTML = repositories.map(repo => `
            <div class="repository-item">
                <div class="repository-info">
                    <h3>${repo.name}</h3>
                    <p><strong>URL:</strong> ${repo.url}</p>
                    <p><strong>Provider:</strong> ${repo.provider} | <strong>Status:</strong> 
                        <span class="status-${repo.sync_status}">${repo.sync_status}</span>
                    </p>
                </div>
                <div class="repository-actions">
                    <button class="btn btn-primary" onclick="app.syncRepository(${repo.id})" 
                        ${repo.sync_status === 'syncing' ? 'disabled' : ''}>
                        ${repo.sync_status === 'syncing' ? 'Syncing...' : 'Sync'}
                    </button>
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
                alert('Repository added successfully! Sync started in background.');
            }
        } catch (error) {
            console.error('Failed to add repository:', error);
            alert('Failed to add repository. Please check the URL and try again.');
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

    updateUserDisplay(userInfo) {
        const navUser = document.getElementById('nav-user');
        if (navUser && userInfo) {
            navUser.textContent = `Welcome, ${userInfo.full_name || userInfo.username}!`;
        }
    }

    async handleSettings(e) {
        e.preventDefault();
        // TODO: Implement settings save
        alert('Settings saved successfully!');
    }

    // GitHub User Management Methods
    showAddGitHubUserForm() {
        document.getElementById('add-github-user-form').style.display = 'block';
    }

    hideAddGitHubUserForm() {
        document.getElementById('add-github-user-form').style.display = 'none';
        document.getElementById('github-user-form').reset();
    }

    async handleAddGitHubUser(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const username = formData.get('github-username');

        try {
            const result = await this.apiCall('/github/users', {
                method: 'POST',
                body: JSON.stringify({
                    username: username
                })
            });

            if (result) {
                this.hideAddGitHubUserForm();
                this.loadGitHubUsers();
                alert(`GitHub user ${username} added successfully!`);
            }
        } catch (error) {
            console.error('Failed to add GitHub user:', error);
            alert('Failed to add GitHub user. Please check the username and try again.');
        }
    }

    async loadGitHubUsers() {
        try {
            const users = await this.apiCall('/github/users');
            this.renderGitHubUsers(users || []);
        } catch (error) {
            console.error('Failed to load GitHub users:', error);
        }
    }

    renderGitHubUsers(users) {
        const container = document.getElementById('github-users-list');
        if (!container) return;

        if (users.length === 0) {
            container.innerHTML = `
                <div class="github-user-item">
                    <p>No GitHub users added yet. Click "Add GitHub User" to start monitoring repositories.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = users.map(user => `
            <div class="github-user-item">
                <img src="${user.avatar_url || '/static/default-avatar.png'}" 
                     alt="${user.username}" class="github-user-avatar">
                <div class="github-user-info">
                    <h3>${user.display_name || user.username}</h3>
                    <p><strong>@${user.username}</strong></p>
                    <div class="github-user-stats">
                        <span class="stat-badge">📚 ${user.public_repos} repos</span>
                        <span class="stat-badge">👥 ${user.followers} followers</span>
                        <span class="stat-badge">🔄 Last synced: ${user.last_synced_at ? new Date(user.last_synced_at).toLocaleDateString() : 'Never'}</span>
                    </div>
                </div>
                <div class="github-user-actions">
                    <button class="btn btn-primary" onclick="app.openRepositorySelection(${user.id}, '${user.username}')">
                        Manage Repositories
                    </button>
                    <button class="btn btn-secondary" onclick="app.removeGitHubUser(${user.id}, '${user.username}')">
                        Remove User
                    </button>
                </div>
            </div>
        `).join('');
    }

    async removeGitHubUser(userId, username) {
        if (confirm(`Are you sure you want to remove GitHub user ${username}? This will also remove all associated repository selections.`)) {
            try {
                await this.apiCall(`/github/users/${userId}`, {
                    method: 'DELETE'
                });
                this.loadGitHubUsers();
                alert(`GitHub user ${username} removed successfully.`);
            } catch (error) {
                console.error('Failed to remove GitHub user:', error);
                alert('Failed to remove GitHub user.');
            }
        }
    }

    // Repository Selection Modal Methods
    async openRepositorySelection(userId, username) {
        this.currentGitHubUserId = userId;
        this.currentGitHubUsername = username;
        
        document.getElementById('modal-title').textContent = `Select Repositories for @${username}`;
        document.getElementById('repo-selection-modal').style.display = 'flex';
        
        // Load repositories with refresh to get latest from GitHub
        await this.loadUserRepositories(userId, true);
    }

    closeRepoSelectionModal() {
        document.getElementById('repo-selection-modal').style.display = 'none';
        this.currentGitHubUserId = null;
        this.currentGitHubUsername = null;
        this.currentRepositories = [];
    }

    async loadUserRepositories(userId, refresh = false) {
        try {
            const repositories = await this.apiCall(`/github/users/${userId}/repositories?refresh=${refresh}`);
            this.currentRepositories = repositories || [];
            this.renderRepositorySelection(this.currentRepositories);
            this.populateLanguageFilter(this.currentRepositories);
        } catch (error) {
            console.error('Failed to load user repositories:', error);
            alert('Failed to load repositories. Please try again.');
        }
    }

    renderRepositorySelection(repositories) {
        const container = document.getElementById('repositories-grid');
        if (!container) return;

        if (repositories.length === 0) {
            container.innerHTML = '<p>No repositories found for this user.</p>';
            return;
        }

        container.innerHTML = repositories.map(repo => `
            <div class="repo-selection-item ${repo.status}" data-repo-id="${repo.id}">
                <div class="status-indicator status-${repo.status}"></div>
                <input type="checkbox" class="repo-checkbox" 
                       ${repo.status === 'selected' ? 'checked' : ''} 
                       onchange="app.toggleRepositorySelection(${repo.id}, this.checked)">
                <div class="repo-info">
                    <h4>${repo.name}</h4>
                    <p>${repo.description || 'No description available'}</p>
                    <div class="repo-meta">
                        ${repo.language ? `<span class="language">${repo.language}</span>` : ''}
                        <span class="stars">⭐ ${repo.stargazers_count}</span>
                        <span class="forks">🍴 ${repo.forks_count}</span>
                        <span>📁 ${(repo.size / 1024).toFixed(1)}MB</span>
                        ${repo.is_private ? '<span>🔒 Private</span>' : '<span>🌍 Public</span>'}
                        ${repo.is_fork ? '<span>🍴 Fork</span>' : ''}
                        ${repo.is_archived ? '<span>📦 Archived</span>' : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }

    populateLanguageFilter(repositories) {
        const languageFilter = document.getElementById('language-filter');
        if (!languageFilter) return;

        // Get unique languages
        const languages = [...new Set(repositories.map(repo => repo.language).filter(lang => lang))];
        languages.sort();

        // Clear existing options except "All Languages"
        languageFilter.innerHTML = '<option value="">All Languages</option>';
        
        // Add language options
        languages.forEach(language => {
            const option = document.createElement('option');
            option.value = language;
            option.textContent = language;
            languageFilter.appendChild(option);
        });
    }

    async toggleRepositorySelection(repoId, isSelected) {
        const status = isSelected ? 'selected' : 'deselected';
        
        try {
            await this.apiCall(`/github/users/${this.currentGitHubUserId}/repositories/bulk-update`, {
                method: 'POST',
                body: JSON.stringify({
                    repository_ids: [repoId],
                    status: status
                })
            });

            // Update local state
            const repo = this.currentRepositories.find(r => r.id === repoId);
            if (repo) {
                repo.status = status;
            }

            // Update visual state
            const repoElement = document.querySelector(`[data-repo-id="${repoId}"]`);
            if (repoElement) {
                repoElement.className = `repo-selection-item ${status}`;
                const statusIndicator = repoElement.querySelector('.status-indicator');
                statusIndicator.className = `status-indicator status-${status}`;
            }

        } catch (error) {
            console.error('Failed to update repository selection:', error);
            // Revert checkbox state
            const checkbox = document.querySelector(`[data-repo-id="${repoId}"] .repo-checkbox`);
            if (checkbox) {
                checkbox.checked = !isSelected;
            }
        }
    }

    async selectAllRepositories() {
        const repositoryIds = this.currentRepositories.map(repo => repo.id);
        await this.bulkUpdateRepositories(repositoryIds, 'selected');
    }

    async deselectAllRepositories() {
        const repositoryIds = this.currentRepositories.map(repo => repo.id);
        await this.bulkUpdateRepositories(repositoryIds, 'deselected');
    }

    async bulkUpdateRepositories(repositoryIds, status) {
        try {
            await this.apiCall(`/github/users/${this.currentGitHubUserId}/repositories/bulk-update`, {
                method: 'POST',
                body: JSON.stringify({
                    repository_ids: repositoryIds,
                    status: status
                })
            });

            // Refresh the repository list
            await this.loadUserRepositories(this.currentGitHubUserId, false);
            
        } catch (error) {
            console.error('Failed to bulk update repositories:', error);
            alert('Failed to update repository selections.');
        }
    }

    async syncSelectedRepositories() {
        try {
            const result = await this.apiCall(`/github/users/${this.currentGitHubUserId}/repositories/sync-selected`, {
                method: 'POST'
            });

            if (result) {
                alert(result.message || 'Selected repositories synced successfully!');
                // Refresh the repository list to show updated sync status
                await this.loadUserRepositories(this.currentGitHubUserId, false);
            }
        } catch (error) {
            console.error('Failed to sync selected repositories:', error);
            alert('Failed to sync repositories. Please try again.');
        }
    }

    filterRepositories() {
        const searchTerm = document.getElementById('repo-search').value.toLowerCase();
        const selectedLanguage = document.getElementById('language-filter').value;

        const filtered = this.currentRepositories.filter(repo => {
            const matchesSearch = repo.name.toLowerCase().includes(searchTerm) || 
                                (repo.description && repo.description.toLowerCase().includes(searchTerm));
            const matchesLanguage = !selectedLanguage || repo.language === selectedLanguage;
            
            return matchesSearch && matchesLanguage;
        });

        this.renderRepositorySelection(filtered);
    }

    // Tab Management
    switchTab(tab) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`${tab}-tab`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.style.display = 'none';
        });
        document.getElementById(`${tab}-content`).style.display = 'block';

        // Load data if needed
        if (tab === 'organizations') {
            this.loadGitHubOrganizations();
        }
    }

    // GitHub Organization Management Methods
    showOAuthModal() {
        document.getElementById('oauth-modal').style.display = 'flex';
    }

    hideOAuthModal() {
        document.getElementById('oauth-modal').style.display = 'none';
    }

    async startGitHubOAuth() {
        try {
            const response = await this.apiCall('/github/organizations/connect', {
                method: 'POST'
            });

            if (response && response.auth_url) {
                // Store the state for security verification
                localStorage.setItem('oauth_state', response.state);
                
                // Open GitHub OAuth in new window
                const authWindow = window.open(
                    response.auth_url,
                    'github-oauth',
                    'width=600,height=700,scrollbars=yes,resizable=yes'
                );

                // Listen for the OAuth callback
                this.listenForOAuthCallback(authWindow);
            }
        } catch (error) {
            console.error('Failed to start OAuth flow:', error);
            alert('Failed to start GitHub OAuth. Please try again.');
        }
    }

    listenForOAuthCallback(authWindow) {
        const checkClosed = setInterval(() => {
            if (authWindow.closed) {
                clearInterval(checkClosed);
                this.hideOAuthModal();
                // Refresh organizations list
                this.loadGitHubOrganizations();
            }
        }, 1000);

        // Listen for message from OAuth window
        const messageListener = (event) => {
            if (event.data.type === 'oauth-success') {
                clearInterval(checkClosed);
                authWindow.close();
                this.hideOAuthModal();
                this.loadGitHubOrganizations();
                alert('GitHub organizations connected successfully!');
                window.removeEventListener('message', messageListener);
            } else if (event.data.type === 'oauth-error') {
                clearInterval(checkClosed);
                authWindow.close();
                this.hideOAuthModal();
                alert('OAuth authorization failed. Please try again.');
                window.removeEventListener('message', messageListener);
            }
        };

        window.addEventListener('message', messageListener);
    }

    async loadGitHubOrganizations() {
        try {
            const organizations = await this.apiCall('/github/organizations');
            this.renderGitHubOrganizations(organizations || []);
        } catch (error) {
            console.error('Failed to load GitHub organizations:', error);
        }
    }

    renderGitHubOrganizations(organizations) {
        const container = document.getElementById('github-organizations-list');
        if (!container) return;

        if (organizations.length === 0) {
            container.innerHTML = `
                <div class="github-organization-item">
                    <p>No GitHub organizations connected yet. Click "Connect Organization" to start monitoring organization repositories.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = organizations.map(org => `
            <div class="github-organization-item">
                <img src="${org.avatar_url || '/static/default-org-avatar.png'}" 
                     alt="${org.login}" class="github-organization-avatar">
                <div class="github-organization-info">
                    <h3>${org.display_name || org.login}</h3>
                    <p><strong>@${org.login}</strong></p>
                    ${org.description ? `<p>${org.description}</p>` : ''}
                    <div class="github-user-stats">
                        <span class="stat-badge">📚 ${org.public_repos} repos</span>
                        <span class="stat-badge">🔄 Last synced: ${org.last_synced_at ? new Date(org.last_synced_at).toLocaleDateString() : 'Never'}</span>
                    </div>
                    <span class="oauth-status connected">OAuth Connected</span>
                </div>
                <div class="github-organization-actions">
                    <button class="btn btn-primary" onclick="app.openOrganizationRepositorySelection(${org.id}, '${org.login}')">
                        Manage Repositories
                    </button>
                    <button class="btn btn-secondary" onclick="app.removeGitHubOrganization(${org.id}, '${org.login}')">
                        Disconnect
                    </button>
                </div>
            </div>
        `).join('');
    }

    async removeGitHubOrganization(orgId, orgLogin) {
        if (confirm(`Are you sure you want to disconnect GitHub organization ${orgLogin}? This will also remove all associated repository selections.`)) {
            try {
                await this.apiCall(`/github/organizations/${orgId}`, {
                    method: 'DELETE'
                });
                this.loadGitHubOrganizations();
                alert(`GitHub organization ${orgLogin} disconnected successfully.`);
            } catch (error) {
                console.error('Failed to remove GitHub organization:', error);
                alert('Failed to disconnect GitHub organization.');
            }
        }
    }

    // Organization Repository Selection Methods
    async openOrganizationRepositorySelection(orgId, orgLogin) {
        this.currentGitHubOrgId = orgId;
        this.currentGitHubOrgLogin = orgLogin;
        this.isOrganizationMode = true;
        
        document.getElementById('modal-title').textContent = `Select Repositories for @${orgLogin}`;
        document.getElementById('repo-selection-modal').style.display = 'flex';
        
        // Load repositories with refresh to get latest from GitHub
        await this.loadOrganizationRepositories(orgId, true);
    }

    async loadOrganizationRepositories(orgId, refresh = false) {
        try {
            const repositories = await this.apiCall(`/github/organizations/${orgId}/repositories?refresh=${refresh}`);
            this.currentRepositories = repositories || [];
            this.renderRepositorySelection(this.currentRepositories);
            this.populateLanguageFilter(this.currentRepositories);
        } catch (error) {
            console.error('Failed to load organization repositories:', error);
            alert('Failed to load repositories. Please try again.');
        }
    }

    // Updated methods to handle both users and organizations
    async toggleRepositorySelection(repoId, isSelected) {
        const status = isSelected ? 'selected' : 'deselected';
        
        const endpoint = this.isOrganizationMode 
            ? `/github/organizations/${this.currentGitHubOrgId}/repositories/bulk-update`
            : `/github/users/${this.currentGitHubUserId}/repositories/bulk-update`;
        
        try {
            await this.apiCall(endpoint, {
                method: 'POST',
                body: JSON.stringify({
                    repository_ids: [repoId],
                    status: status
                })
            });

            // Update local state
            const repo = this.currentRepositories.find(r => r.id === repoId);
            if (repo) {
                repo.status = status;
            }

            // Update visual state
            const repoElement = document.querySelector(`[data-repo-id="${repoId}"]`);
            if (repoElement) {
                repoElement.className = `repo-selection-item ${status}`;
                const statusIndicator = repoElement.querySelector('.status-indicator');
                statusIndicator.className = `status-indicator status-${status}`;
            }

        } catch (error) {
            console.error('Failed to update repository selection:', error);
            // Revert checkbox state
            const checkbox = document.querySelector(`[data-repo-id="${repoId}"] .repo-checkbox`);
            if (checkbox) {
                checkbox.checked = !isSelected;
            }
        }
    }

    async bulkUpdateRepositories(repositoryIds, status) {
        const endpoint = this.isOrganizationMode 
            ? `/github/organizations/${this.currentGitHubOrgId}/repositories/bulk-update`
            : `/github/users/${this.currentGitHubUserId}/repositories/bulk-update`;

        try {
            await this.apiCall(endpoint, {
                method: 'POST',
                body: JSON.stringify({
                    repository_ids: repositoryIds,
                    status: status
                })
            });

            // Refresh the repository list
            if (this.isOrganizationMode) {
                await this.loadOrganizationRepositories(this.currentGitHubOrgId, false);
            } else {
                await this.loadUserRepositories(this.currentGitHubUserId, false);
            }
            
        } catch (error) {
            console.error('Failed to bulk update repositories:', error);
            alert('Failed to update repository selections.');
        }
    }

    async syncSelectedRepositories() {
        const endpoint = this.isOrganizationMode 
            ? `/github/organizations/${this.currentGitHubOrgId}/repositories/sync-selected`
            : `/github/users/${this.currentGitHubUserId}/repositories/sync-selected`;

        try {
            const result = await this.apiCall(endpoint, {
                method: 'POST'
            });

            if (result) {
                alert(result.message || 'Selected repositories synced successfully!');
                // Refresh the repository list to show updated sync status
                if (this.isOrganizationMode) {
                    await this.loadOrganizationRepositories(this.currentGitHubOrgId, false);
                } else {
                    await this.loadUserRepositories(this.currentGitHubUserId, false);
                }
            }
        } catch (error) {
            console.error('Failed to sync selected repositories:', error);
            alert('Failed to sync repositories. Please try again.');
        }
    }

    closeRepoSelectionModal() {
        document.getElementById('repo-selection-modal').style.display = 'none';
        this.currentGitHubUserId = null;
        this.currentGitHubUsername = null;
        this.currentGitHubOrgId = null;
        this.currentGitHubOrgLogin = null;
        this.isOrganizationMode = false;
        this.currentRepositories = [];
    }

    // Task Management Methods
    async loadTaskData() {
        try {
            // Load task statistics
            const stats = await this.apiCall('/tasks/stats');
            this.updateTaskStatistics(stats);

            // Load active tasks (placeholder)
            this.renderActiveTasks([]);
            
            // Load task history (placeholder)  
            this.renderTaskHistory([]);
            
        } catch (error) {
            console.error('Failed to load task data:', error);
        }
    }

    updateTaskStatistics(stats) {
        if (stats && stats.repository_sync) {
            document.getElementById('completed-repos').textContent = stats.repository_sync.completed;
            document.getElementById('failed-repos').textContent = stats.repository_sync.failed;
            document.getElementById('pending-repos').textContent = stats.repository_sync.pending;
        }

        if (stats && stats.github_sources) {
            document.getElementById('github-users-count').textContent = stats.github_sources.users;
            document.getElementById('github-orgs-count').textContent = stats.github_sources.organizations;
        }
    }

    renderActiveTasks(tasks) {
        const container = document.getElementById('active-tasks-list');
        if (!container) return;

        if (tasks.length === 0) {
            container.innerHTML = '<div class="empty-tasks">No active tasks running</div>';
            return;
        }

        container.innerHTML = tasks.map(task => this.createTaskHTML(task)).join('');
    }

    renderTaskHistory(tasks) {
        const container = document.getElementById('task-history-list');
        if (!container) return;

        if (tasks.length === 0) {
            container.innerHTML = '<div class="empty-tasks">No recent task history</div>';
            return;
        }

        container.innerHTML = tasks.map(task => this.createTaskHTML(task, false)).join('');
    }

    createTaskHTML(task, showActions = true) {
        const statusClass = task.status?.toLowerCase() || 'pending';
        const progress = task.progress || 0;
        
        return `
            <div class="task-item ${statusClass}" data-task-id="${task.task_id}">
                <div class="task-header">
                    <h4 class="task-title">${task.task_name || 'Background Task'}</h4>
                    <span class="task-status ${statusClass}">${task.status || 'pending'}</span>
                </div>
                
                ${progress > 0 ? `
                    <div class="task-progress">
                        <div class="progress-bar">
                            <div class="progress-fill ${statusClass}" style="width: ${progress}%"></div>
                        </div>
                        <div class="progress-text">${progress}% complete</div>
                    </div>
                ` : ''}
                
                <div class="task-details">
                    <div class="task-detail">
                        <span class="task-detail-label">Task ID</span>
                        <span class="task-detail-value">${task.task_id}</span>
                    </div>
                    <div class="task-detail">
                        <span class="task-detail-label">Started</span>
                        <span class="task-detail-value">${task.created_at || 'Unknown'}</span>
                    </div>
                    ${task.meta?.status ? `
                        <div class="task-detail">
                            <span class="task-detail-label">Status</span>
                            <span class="task-detail-value">${task.meta.status}</span>
                        </div>
                    ` : ''}
                </div>
                
                ${showActions && (statusClass === 'pending' || statusClass === 'running') ? `
                    <div class="task-actions">
                        <button class="btn btn-sm btn-secondary" onclick="app.cancelTask('${task.task_id}')">
                            Cancel
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="app.refreshTaskStatus('${task.task_id}')">
                            Refresh
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    }

    async startBulkSync() {
        try {
            // Get all repositories for bulk sync
            const repositories = await this.apiCall('/repositories');
            
            if (!repositories || repositories.length === 0) {
                alert('No repositories available for bulk sync');
                return;
            }

            const repoIds = repositories.map(repo => repo.id);
            
            if (confirm(`Start bulk sync for ${repoIds.length} repositories? This may take several minutes.`)) {
                const response = await this.apiCall('/tasks/repositories/bulk-sync', {
                    method: 'POST',
                    body: JSON.stringify({
                        repository_ids: repoIds
                    })
                });

                if (response) {
                    alert(`Bulk sync started! Task ID: ${response.task_id}`);
                    this.startTaskMonitoring(response.task_id);
                }
            }
        } catch (error) {
            console.error('Failed to start bulk sync:', error);
            alert('Failed to start bulk sync. Please try again.');
        }
    }

    async cancelTask(taskId) {
        try {
            const response = await this.apiCall(`/tasks/cancel/${taskId}`, {
                method: 'DELETE'
            });

            if (response) {
                alert(response.message);
                this.loadTaskData();
            }
        } catch (error) {
            console.error('Failed to cancel task:', error);
            alert('Failed to cancel task.');
        }
    }

    async refreshTaskStatus(taskId) {
        try {
            const response = await this.apiCall(`/tasks/status/${taskId}`);
            
            if (response) {
                // Update the task item in the UI
                const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
                if (taskElement) {
                    const newHTML = this.createTaskHTML({
                        task_id: taskId,
                        status: response.status,
                        progress: response.progress,
                        meta: response.meta,
                        task_name: 'Background Task'
                    });
                    taskElement.outerHTML = newHTML;
                }
            }
        } catch (error) {
            console.error('Failed to refresh task status:', error);
        }
    }

    startTaskMonitoring(taskId) {
        // Monitor task progress every 2 seconds
        const monitor = setInterval(async () => {
            try {
                const response = await this.apiCall(`/tasks/status/${taskId}`);
                
                if (response) {
                    this.refreshTaskStatus(taskId);
                    
                    // Stop monitoring if task is completed or failed
                    if (response.status === 'success' || response.status === 'failure') {
                        clearInterval(monitor);
                        this.loadTaskData(); // Refresh the entire task list
                    }
                }
            } catch (error) {
                console.error('Error monitoring task:', error);
                clearInterval(monitor);
            }
        }, 2000);

        // Stop monitoring after 10 minutes to prevent endless polling
        setTimeout(() => {
            clearInterval(monitor);
        }, 600000);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new GitAnalyticsApp();
});