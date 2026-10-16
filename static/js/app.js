// Aatam - Board Game Wiki on Steroids Client App

let state = {
  currentView: 'explorer',
  activeUser: localStorage.getItem('aatam_user') || 'PlayerOne',
  authToken: localStorage.getItem('aatam_token') || null,
  currentUser: null,
  searchQuery: '',
  selectedCategory: '',
  selectedWeight: '',
  sortBy: 'bayes_avg_rating',
  page: 1,
  totalPages: 1,
  currentGame: null,
  activeVideoPollInterval: null,
  activeLogGameId: null,
  onboardingSelectedGames: []
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  checkAuthStatus();
  loadGames();
  loadLLMConfig();
});

// Navigation
function navigate(viewName) {
  if (!state.currentUser) {
    openAuthModal('signup');
    showToast("An account is required to explore Aatam Wiki. Please sign in or create an account.", true);
    return;
  }

  state.currentView = viewName;
  ['explorer', 'recommender', 'shelf', 'studio', 'submit'].forEach(v => {
    const el = document.getElementById(`view-${v}`);
    const navBtn = document.getElementById(`nav-${v}`);
    const navMobileBtn = document.getElementById(`nav-${v}-mobile`);
    if (v === viewName) {
      if (el) el.classList.remove('hidden');
      if (navBtn) {
        navBtn.className = "nav-btn px-3 py-2 rounded-lg text-sm font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 flex items-center space-x-2 transition";
      }
      if (navMobileBtn) {
        navMobileBtn.className = "nav-btn-mobile px-3 py-2 rounded-lg text-sm font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 flex items-center space-x-2 transition";
      }
    } else {
      if (el) el.classList.add('hidden');
      if (navBtn) {
        navBtn.className = "nav-btn px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 flex items-center space-x-2 transition";
      }
      if (navMobileBtn) {
        navMobileBtn.className = "nav-btn-mobile px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 flex items-center space-x-2 transition";
      }
    }
  });

  if (viewName === 'recommender') {
    loadRecommendations();
  } else if (viewName === 'shelf') {
    loadUserShelf();
  } else if (viewName === 'studio') {
    loadStudioGame();
  } else if (viewName === 'submit') {
    const guard = document.getElementById('submit-auth-guard');
    const container = document.getElementById('submit-form-container');
    if (state.currentUser) {
      if (guard) guard.classList.add('hidden');
      if (container) container.classList.remove('hidden');
    } else {
      if (guard) guard.classList.remove('hidden');
      if (container) container.classList.add('hidden');
    }
    loadCommunitySubmissions();
  }
  lucide.createIcons();
}

// ==========================================
// AUTHENTICATION & USER SESSIONS
// ==========================================
async function checkAuthStatus() {
  const token = state.authToken;
  if (!token) {
    state.currentUser = null;
    updateAuthUI();
    loadUserList();
    openAuthModal('signup');
    return;
  }

  try {
    const res = await fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      state.currentUser = data.user;
      state.activeUser = data.user.username;
      localStorage.setItem('aatam_user', data.user.username);
    } else {
      // Invalid/expired token
      state.authToken = null;
      state.currentUser = null;
      localStorage.removeItem('aatam_token');
      openAuthModal('signup');
    }
  } catch (e) {
    console.warn("Auth check failed:", e);
    openAuthModal('signup');
  }

  updateAuthUI();
  loadUserList();
}

function updateAuthUI() {
  const loggedOutDiv = document.getElementById('auth-logged-out');
  const loggedInDiv = document.getElementById('auth-logged-in');
  const closeBtn = document.getElementById('auth-modal-close-btn');

  if (state.currentUser) {
    if (loggedOutDiv) loggedOutDiv.classList.add('hidden');
    if (loggedInDiv) loggedInDiv.classList.remove('hidden');
    if (closeBtn) closeBtn.classList.remove('hidden');

    const nameEl = document.getElementById('active-user-name');
    const emailEl = document.getElementById('active-user-email');
    const avatarEl = document.getElementById('user-avatar-text');
    const dropName = document.getElementById('dropdown-full-name');
    const dropEmail = document.getElementById('dropdown-full-email');

    const u = state.currentUser;
    if (nameEl) nameEl.textContent = u.display_name || u.username;
    if (emailEl) emailEl.textContent = u.email || 'Verified Gamer';
    if (avatarEl) avatarEl.textContent = (u.display_name || u.username).substring(0, 2).toUpperCase();
    if (dropName) dropName.textContent = `${u.display_name || u.username} (@${u.username})`;
    if (dropEmail) dropEmail.textContent = u.email || '';
  } else {
    if (loggedOutDiv) loggedOutDiv.classList.remove('hidden');
    if (loggedInDiv) loggedInDiv.classList.add('hidden');
    if (closeBtn) closeBtn.classList.add('hidden');
  }
}

function openAuthModal(tab = 'signup') {
  const modal = document.getElementById('auth-modal');
  const closeBtn = document.getElementById('auth-modal-close-btn');
  modal.classList.remove('hidden');
  if (closeBtn) {
    if (state.currentUser) {
      closeBtn.classList.remove('hidden');
    } else {
      closeBtn.classList.add('hidden');
    }
  }
  hideAuthError();
  switchAuthTab(tab);
}

function closeAuthModal() {
  if (!state.currentUser) {
    showToast("An account is required to use Aatam Wiki. Please sign in or create an account.", true);
    return;
  }
  document.getElementById('auth-modal').classList.add('hidden');
}

function switchAuthTab(tab) {
  const signupForm = document.getElementById('auth-signup-form');
  const loginForm = document.getElementById('auth-login-form');
  const signupBtn = document.getElementById('auth-tab-btn-signup');
  const loginBtn = document.getElementById('auth-tab-btn-login');
  const modalTitle = document.getElementById('auth-modal-title');

  hideAuthError();

  if (tab === 'signup') {
    signupForm.classList.remove('hidden');
    loginForm.classList.add('hidden');
    signupBtn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold bg-amber-500 text-slate-950 shadow-sm transition";
    loginBtn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold text-slate-300 hover:text-white transition";
    modalTitle.textContent = "Join Aatam Wiki";
  } else {
    signupForm.classList.add('hidden');
    loginForm.classList.remove('hidden');
    loginBtn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold bg-amber-500 text-slate-950 shadow-sm transition";
    signupBtn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold text-slate-300 hover:text-white transition";
    modalTitle.textContent = "Welcome Back to Aatam";
  }
}

function showAuthError(msg) {
  const alertBox = document.getElementById('auth-error-alert');
  const textEl = document.getElementById('auth-error-msg');
  if (alertBox && textEl) {
    textEl.textContent = msg;
    alertBox.classList.remove('hidden');
  }
}

function hideAuthError() {
  const alertBox = document.getElementById('auth-error-alert');
  if (alertBox) alertBox.classList.add('hidden');
}

function toggleOnboardingGame(bggId, gameTitle) {
  const btn = document.querySelector(`.onboard-chip[data-id="${bggId}"]`);
  const checkIcon = btn ? btn.querySelector('i') : null;
  const countEl = document.getElementById('onboarding-selected-count');

  const idx = state.onboardingSelectedGames.indexOf(bggId);
  if (idx > -1) {
    state.onboardingSelectedGames.splice(idx, 1);
    if (btn) btn.className = "onboard-chip text-left p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-white/5 flex items-center justify-between transition";
    if (checkIcon) checkIcon.classList.add('hidden');
  } else {
    state.onboardingSelectedGames.push(bggId);
    if (btn) btn.className = "onboard-chip text-left p-2 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center justify-between transition";
    if (checkIcon) checkIcon.classList.remove('hidden');
  }

  if (countEl) {
    countEl.textContent = `${state.onboardingSelectedGames.length} selected`;
  }
}

async function handleSignUpSubmit(e) {
  e.preventDefault();
  hideAuthError();

  const email = document.getElementById('auth-signup-email').value.trim();
  const username = document.getElementById('auth-signup-username').value.trim();
  const displayName = document.getElementById('auth-signup-name').value.trim();
  const password = document.getElementById('auth-signup-password').value;
  const btn = document.getElementById('auth-signup-submit-btn');

  btn.disabled = true;
  btn.classList.add('opacity-50');

  try {
    const res = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email,
        username: username,
        password: password,
        display_name: displayName || username,
        played_games: state.onboardingSelectedGames
      })
    });
    const data = await res.json();
    btn.disabled = false;
    btn.classList.remove('opacity-50');

    if (!res.ok) {
      showAuthError(data.detail || "Sign up failed. Please try again.");
      return;
    }

    state.authToken = data.token;
    state.currentUser = data.user;
    state.activeUser = data.user.username;
    localStorage.setItem('aatam_token', data.token);
    localStorage.setItem('aatam_user', data.user.username);

    updateAuthUI();
    closeAuthModal();
    showToast(`Welcome to Aatam, ${data.user.display_name}! Initialized with ${state.onboardingSelectedGames.length} played games.`);
    loadUserList();
    if (state.currentView === 'shelf') loadUserShelf();
    if (state.currentView === 'recommender') loadRecommendations();
  } catch (err) {
    btn.disabled = false;
    btn.classList.remove('opacity-50');
    showAuthError(`Network error: ${err.message}`);
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  hideAuthError();

  const loginId = document.getElementById('auth-login-id').value.trim();
  const password = document.getElementById('auth-login-password').value;
  const btn = document.getElementById('auth-login-submit-btn');

  btn.disabled = true;
  btn.classList.add('opacity-50');

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login_id: loginId, password: password })
    });
    const data = await res.json();
    btn.disabled = false;
    btn.classList.remove('opacity-50');

    if (!res.ok) {
      showAuthError(data.detail || "Invalid credentials.");
      return;
    }

    state.authToken = data.token;
    state.currentUser = data.user;
    state.activeUser = data.user.username;
    localStorage.setItem('aatam_token', data.token);
    localStorage.setItem('aatam_user', data.user.username);

    updateAuthUI();
    closeAuthModal();
    showToast(`Welcome back, ${data.user.display_name}!`);
    loadUserList();
    if (state.currentView === 'shelf') loadUserShelf();
    if (state.currentView === 'recommender') loadRecommendations();
  } catch (err) {
    btn.disabled = false;
    btn.classList.remove('opacity-50');
    showAuthError(`Network error: ${err.message}`);
  }
}

async function handleLogout() {
  if (state.authToken) {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${state.authToken}` }
      });
    } catch (e) {}
  }
  state.authToken = null;
  state.currentUser = null;
  state.activeUser = 'PlayerOne';
  localStorage.removeItem('aatam_token');
  localStorage.setItem('aatam_user', 'PlayerOne');

  const menu = document.getElementById('user-dropdown-menu');
  if (menu) menu.classList.add('hidden');

  updateAuthUI();
  showToast("You have been signed out.");
  loadUserList();
  if (state.currentView === 'shelf') loadUserShelf();
  if (state.currentView === 'recommender') loadRecommendations();
}

// User List & Showcase Critics
async function loadUserList() {
  try {
    const res = await fetch('/api/users');
    const data = await res.json();
    const container = document.getElementById('user-list-container');
    if (!container) return;
    container.innerHTML = '';
    
    data.users.forEach(u => {
      const btn = document.createElement('button');
      btn.className = `w-full text-left px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-between transition ${u.username === state.activeUser ? 'bg-amber-500/20 text-amber-300' : 'text-slate-300 hover:bg-slate-800'}`;
      btn.innerHTML = `
        <span class="truncate">${u.display_name || u.username}</span>
        <span class="text-[10px] text-slate-500 ml-2">${u.total_ratings} plays</span>
      `;
      btn.onclick = () => switchUser(u.username);
      container.appendChild(btn);
    });
  } catch (e) {
    console.error("Error loading users:", e);
  }
}

function toggleUserDropdown() {
  const menu = document.getElementById('user-dropdown-menu');
  if (menu) menu.classList.toggle('hidden');
}

function switchUser(username) {
  state.activeUser = username;
  localStorage.setItem('aatam_user', username);
  const menu = document.getElementById('user-dropdown-menu');
  if (menu) menu.classList.add('hidden');
  showToast(`Viewing collection as ${username}`);
  loadUserList();
  if (state.currentView === 'shelf') loadUserShelf();
  if (state.currentView === 'recommender') loadRecommendations();
}


// ==========================================
// VIEW 1: WIKI EXPLORER
// ==========================================
let searchDebounceTimeout = null;
function handleSearchInput(e) {
  state.searchQuery = e.target.value.trim();
  clearTimeout(searchDebounceTimeout);
  searchDebounceTimeout = setTimeout(() => {
    state.page = 1;
    loadGames();
  }, 300);
}

function handleFilterChange() {
  state.sortBy = document.getElementById('sort-select').value;
  state.selectedWeight = document.getElementById('weight-filter').value;
  state.page = 1;
  loadGames();
}

function setCategoryFilter(cat) {
  state.selectedCategory = cat;
  document.querySelectorAll('.cat-pill').forEach(btn => {
    if ((cat === '' && btn.innerText.includes('All')) || btn.innerText.includes(cat)) {
      btn.className = "cat-pill active px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 whitespace-nowrap";
    } else {
      btn.className = "cat-pill px-3 py-1 rounded-full bg-slate-800 text-slate-300 hover:bg-slate-700 whitespace-nowrap";
    }
  });
  state.page = 1;
  loadGames();
}

async function loadGames() {
  const grid = document.getElementById('games-grid');
  grid.innerHTML = '<div class="col-span-full py-20 text-center text-slate-400 font-medium">Loading catalog...</div>';

  let url = `/api/games?page=${state.page}&limit=24&sort_by=${state.sortBy}&order=desc`;
  if (state.searchQuery) url += `&q=${encodeURIComponent(state.searchQuery)}`;
  if (state.selectedCategory) url += `&category=${encodeURIComponent(state.selectedCategory)}`;
  
  if (state.selectedWeight === 'light') url += `&max_weight=2.0`;
  else if (state.selectedWeight === 'medium') url += `&min_weight=2.0&max_weight=3.2`;
  else if (state.selectedWeight === 'heavy') url += `&min_weight=3.2`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    state.totalPages = data.total_pages;

    document.getElementById('pagination-info').innerText = `Showing page ${data.page} of ${data.total_pages || 1} (${data.total.toLocaleString()} games)`;
    document.getElementById('prev-page-btn').disabled = data.page <= 1;
    document.getElementById('next-page-btn').disabled = data.page >= data.total_pages;

    grid.innerHTML = '';
    if (!data.games || data.games.length === 0) {
      grid.innerHTML = '<div class="col-span-full py-16 text-center text-slate-400">No board games found matching criteria.</div>';
      return;
    }

    data.games.forEach(g => {
      grid.appendChild(createGameCard(g));
    });
    lucide.createIcons();
  } catch (e) {
    grid.innerHTML = `<div class="col-span-full py-16 text-center text-rose-400">Error loading games: ${e.message}</div>`;
  }
}

function changePage(delta) {
  const newPage = state.page + delta;
  if (newPage >= 1 && newPage <= state.totalPages) {
    state.page = newPage;
    loadGames();
    window.scrollTo({ top: 400, behavior: 'smooth' });
  }
}

function createGameCard(g) {
  const card = document.createElement('div');
  card.className = "game-card glass-panel rounded-2xl p-4 flex flex-col justify-between border border-white/10 glow-card relative overflow-hidden group cursor-pointer";
  card.onclick = (e) => {
    if (!e.target.closest('button')) {
      openGameModal(g.bgg_id);
    }
  };

  const weight = (g.game_weight || 0).toFixed(1);
  const weightPct = Math.min(100, (weight / 5.0) * 100);
  const weightColor = weight < 2.0 ? 'bg-emerald-400' : weight < 3.2 ? 'bg-amber-400' : 'bg-rose-500';

  const bayesRating = (g.bayes_avg_rating || 0).toFixed(1);
  const ratingColor = bayesRating >= 7.5 ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' : 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10';

  const mechs = (g.mechanics || '').split(';').map(m => m.trim()).filter(m => m).slice(0, 2);

  card.innerHTML = `
    <div>
      <!-- Thumbnail & Badges -->
      <div class="relative aspect-[4/3] rounded-xl overflow-hidden bg-slate-950 mb-3.5">
        <img src="${g.image_path || '/static/images/placeholder.jpg'}" alt="${g.name}" 
             onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'300\\' height=\\'225\\' viewBox=\\'0 0 300 225\\'><rect fill=\\'%231e293b\\' width=\\'300\\' height=\\'225\\'/><text fill=\\'%2364748b\\' x=\\'50%\\' y=\\'50%\\' text-anchor=\\'middle\\'>Board Game</text></svg>'"
             class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
        
        <!-- Rating Badge -->
        <div class="absolute top-2.5 left-2.5 px-2 py-1 rounded-lg ${ratingColor} border backdrop-blur-md text-xs font-extrabold flex items-center space-x-1">
          <i data-lucide="star" class="w-3 h-3 fill-current"></i>
          <span>${bayesRating}</span>
        </div>

        ${g.has_video ? `
        <!-- Video Badge -->
        <div class="absolute top-2.5 right-2.5 px-2 py-1 rounded-lg bg-purple-600/90 text-white backdrop-blur-md text-[11px] font-bold flex items-center space-x-1 shadow-lg shadow-purple-600/30 pulse-badge">
          <i data-lucide="clapperboard" class="w-3 h-3"></i>
          <span>Video</span>
        </div>
        ` : ''}

        <div class="absolute bottom-2 left-2 right-2 flex items-center justify-between text-[11px] text-slate-300 font-semibold bg-slate-950/80 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-white/10">
          <span>👥 ${g.min_players === g.max_players ? g.min_players : `${g.min_players}-${g.max_players}`}p</span>
          <span>⏳ ${g.mfg_playtime || 45}m</span>
          <span>${g.year_published || ''}</span>
        </div>
      </div>

      <!-- Title & Year -->
      <h3 class="font-extrabold text-white text-base leading-snug group-hover:text-amber-400 transition line-clamp-1">${g.name}</h3>
      
      <!-- Complexity Weight Gauge -->
      <div class="mt-2.5 space-y-1">
        <div class="flex justify-between text-[11px] text-slate-400 font-medium">
          <span>Weight</span>
          <span class="font-bold text-slate-200">${weight} / 5</span>
        </div>
        <div class="weight-track">
          <div class="weight-fill ${weightColor}" style="width: ${weightPct}%"></div>
        </div>
      </div>

      <!-- Mechanics Tags -->
      <div class="flex flex-wrap gap-1.5 mt-3">
        ${mechs.map(m => `<span class="px-2 py-0.5 rounded-md bg-slate-800/90 border border-white/5 text-[11px] text-slate-300 truncate max-w-[120px]">${m}</span>`).join('')}
      </div>
    </div>

    <!-- Actions Footer -->
    <div class="mt-4 pt-3 border-t border-white/10 flex items-center justify-between gap-2">
      <button onclick="openGameModal(${g.bgg_id})" class="flex-1 py-1.5 px-3 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-xs font-bold border border-amber-500/20 flex items-center justify-center space-x-1 transition">
        <i data-lucide="${g.has_video ? 'play-circle' : 'info'}" class="w-3.5 h-3.5"></i>
        <span>${g.has_video ? 'Watch Video' : 'Details'}</span>
      </button>
      <button onclick="openLogPlayModal(${g.bgg_id}, '${escapeQuote(g.name)}')" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition" title="Log Play">
        <i data-lucide="plus" class="w-4 h-4"></i>
      </button>
    </div>
  `;
  return card;
}

// ==========================================
// VIEW 2: STEROID RECOMMENDER
// ==========================================
async function loadRecommendations() {
  const grid = document.getElementById('recs-grid');
  const summaryEl = document.getElementById('recommender-taste-summary');

  if (!state.currentUser) {
    summaryEl.textContent = "Sign up with email to unlock hyper-personalized AI recommendation matrices tuned to your shelf.";
    grid.innerHTML = `
      <div class="col-span-full py-16 text-center space-y-4 glass-panel rounded-2xl p-8 border border-white/10">
        <div class="w-16 h-16 rounded-2xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center mx-auto text-2xl font-black">
          <i data-lucide="sparkles" class="w-8 h-8"></i>
        </div>
        <h3 class="text-xl font-black text-white">Unlock Steroid Recommendations</h3>
        <p class="text-sm text-slate-400 max-w-md mx-auto">Create a free account to track your played games, calibrate your complexity affinities, and get game match scores computed across 94,000+ titles.</p>
        <div class="pt-2 flex items-center justify-center gap-3">
          <button onclick="openAuthModal('signup')" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-black text-xs shadow-lg shadow-cyan-500/20 transition">
            Sign Up with Email
          </button>
          <button onclick="openAuthModal('login')" class="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs border border-white/10 transition">
            Sign In
          </button>
        </div>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  grid.innerHTML = '<div class="col-span-full py-20 text-center text-slate-400 font-medium">Finding picks...</div>';

  try {
    const res = await fetch(`/api/users/${state.activeUser}/recommendations?limit=16`);
    const data = await res.json();

    const userRes = await fetch(`/api/users/${state.activeUser}`);
    const userProfile = await userRes.json();

    const topMechStr = userProfile.top_mechanics.slice(0, 3).map(m => m.name).join(', ') || 'Various mechanics';
    summaryEl.textContent = `Based on your ${userProfile.total_played} played games.`;

    grid.innerHTML = '';
    if (!data.recommendations || data.recommendations.length === 0) {
      grid.innerHTML = '<div class="col-span-full py-16 text-center text-slate-400">Rate a few games to get picks.</div>';
      return;
    }

    data.recommendations.forEach(g => {
      const card = document.createElement('div');
      card.className = "game-card glass-panel rounded-2xl p-4 flex flex-col justify-between border border-cyan-500/20 glow-card relative overflow-hidden group cursor-pointer";
      card.onclick = (e) => {
        if (!e.target.closest('button')) openGameModal(g.bgg_id);
      };

      const reasons = g.match_reasons || [];

      card.innerHTML = `
        <div>
          <!-- Thumbnail & Match Badge -->
          <div class="relative aspect-[4/3] rounded-xl overflow-hidden bg-slate-950 mb-3.5">
            <img src="${g.image_path || '/static/images/placeholder.jpg'}" alt="${g.name}" class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
            
            <!-- Match Score Pill -->
            <div class="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/30 text-xs font-black flex items-center space-x-1">
              <i data-lucide="zap" class="w-3.5 h-3.5 fill-current"></i>
              <span>${g.match_score}%</span>
            </div>

            ${g.has_video ? `
            <div class="absolute top-2.5 right-2.5 px-2 py-1 rounded-lg bg-purple-600/90 text-white text-[11px] font-bold flex items-center space-x-1">
              <i data-lucide="clapperboard" class="w-3 h-3"></i>
              <span>Video</span>
            </div>` : ''}

            <div class="absolute bottom-2 left-2 right-2 flex items-between text-[11px] text-slate-300 font-semibold bg-slate-950/80 px-2.5 py-1 rounded-lg border border-white/10">
              <span>👥 ${g.min_players}-${g.max_players}p</span>
              <span class="mx-auto">⏳ ${g.mfg_playtime || 45}m</span>
              <span>⭐ ${(g.bayes_avg_rating||0).toFixed(1)}</span>
            </div>
          </div>

          <h3 class="font-extrabold text-white text-base leading-snug group-hover:text-cyan-400 transition line-clamp-1">${g.name}</h3>
          
          <!-- Recommendation Reasons -->
          <div class="mt-2.5 space-y-1">
            ${reasons.map(r => `
              <div class="flex items-start space-x-1.5 text-xs text-slate-300">
                <i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5"></i>
                <span class="line-clamp-2">${r}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-white/10 flex items-center gap-2">
          <button onclick="openGameModal(${g.bgg_id})" class="flex-1 py-1.5 px-3 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 text-xs font-bold border border-cyan-500/20 flex items-center justify-center space-x-1 transition">
            <i data-lucide="play-circle" class="w-3.5 h-3.5"></i>
            <span>${g.has_video ? 'Watch Explainer' : 'Learn & Video'}</span>
          </button>
          <button onclick="openLogPlayModal(${g.bgg_id}, '${escapeQuote(g.name)}')" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition">
            <i data-lucide="plus" class="w-4 h-4"></i>
          </button>
        </div>
      `;
      grid.appendChild(card);
    });
    lucide.createIcons();
  } catch (e) {
    grid.innerHTML = `<div class="col-span-full py-16 text-center text-rose-400">Failed to load recommendations: ${e.message}</div>`;
  }
}

function refreshRecommendations() {
  loadRecommendations();
  showToast("Refreshed recommendation rankings!");
}

// ==========================================
// VIEW 3: MY SHELF & PLAYS
// ==========================================
async function loadUserShelf() {
  const grid = document.getElementById('shelf-grid');

  if (!state.currentUser) {
    grid.innerHTML = `
      <div class="col-span-full py-16 text-center space-y-4 glass-panel rounded-2xl p-8 border border-white/10">
        <div class="w-16 h-16 rounded-2xl bg-amber-500/20 text-amber-400 flex items-center justify-center mx-auto text-2xl font-black">
          <i data-lucide="lock" class="w-8 h-8"></i>
        </div>
        <h3 class="text-xl font-black text-white">Create an Account to Track Your Plays</h3>
        <p class="text-sm text-slate-400 max-w-md mx-auto">Sign up with your email to log board game plays, rate titles, track personal statistics, and unlock custom AI-driven recommendations.</p>
        <div class="pt-2 flex items-center justify-center gap-3">
          <button onclick="openAuthModal('signup')" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black text-xs shadow-lg shadow-amber-500/20 transition">
            Create Free Account
          </button>
          <button onclick="openAuthModal('login')" class="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs border border-white/10 transition">
            Sign In
          </button>
        </div>
      </div>
    `;
    document.getElementById('shelf-user-name').textContent = "Guest Explorer";
    document.getElementById('shelf-user-bio').textContent = "Sign up with email to start logging your tabletop journey!";
    document.getElementById('shelf-avatar').textContent = "?";
    document.getElementById('stat-total-played').textContent = "0";
    document.getElementById('stat-avg-rating').textContent = "0.0 / 10";
    document.getElementById('stat-pref-weight').textContent = "0.0 / 5";
    document.getElementById('stat-fav-mechanic').textContent = "None";
    document.getElementById('mechanics-affinity-bars').innerHTML = '<div class="text-xs text-slate-500 italic">No plays recorded</div>';
    document.getElementById('rating-dist-chart').innerHTML = '<div class="w-full text-center text-xs text-slate-500 italic py-4">Sign in to view rating curve</div>';
    lucide.createIcons();
    return;
  }

  grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400">Loading your shelf...</div>';

  try {
    const res = await fetch(`/api/users/${state.activeUser}`);
    const data = await res.json();

    document.getElementById('shelf-user-name').textContent = data.user.display_name || data.user.username;
    document.getElementById('shelf-user-bio').textContent = data.user.bio || 'Board Game Enthusiast';
    document.getElementById('shelf-avatar').textContent = state.activeUser.substring(0, 2).toUpperCase();

    document.getElementById('stat-total-played').textContent = data.total_played;
    document.getElementById('stat-avg-rating').textContent = `${data.avg_user_rating} / 10`;
    document.getElementById('stat-pref-weight').textContent = `${data.avg_preferred_weight} / 5`;
    document.getElementById('stat-fav-mechanic').textContent = data.top_mechanics[0]?.name || 'Varied';

    // Top Mechanics Bars
    const mechContainer = document.getElementById('mechanics-affinity-bars');
    mechContainer.innerHTML = '';
    const maxMech = Math.max(...data.top_mechanics.map(m => m.count), 1);
    data.top_mechanics.slice(0, 5).forEach(m => {
      const pct = (m.count / maxMech) * 100;
      mechContainer.innerHTML += `
        <div>
          <div class="flex justify-between text-slate-300 mb-1">
            <span>${m.name}</span>
            <span class="text-amber-400 font-bold">${m.count} plays</span>
          </div>
          <div class="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div class="h-full bg-gradient-to-r from-amber-500 to-amber-300 rounded-full" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    });

    // Rating Distribution Chart
    const distChart = document.getElementById('rating-dist-chart');
    distChart.innerHTML = '';
    const maxDist = Math.max(...Object.values(data.rating_distribution), 1);
    for (let i = 1; i <= 10; i++) {
      const count = data.rating_distribution[i] || 0;
      const heightPct = Math.max(10, (count / maxDist) * 100);
      distChart.innerHTML += `
        <div class="flex-1 flex flex-col items-center gap-1 group">
          <div class="text-[9px] text-slate-400 group-hover:text-white">${count}</div>
          <div class="w-full bg-cyan-500/80 hover:bg-cyan-400 rounded-t transition" style="height: ${heightPct}px"></div>
          <div class="text-[10px] text-slate-400 font-bold">${i}★</div>
        </div>
      `;
    }

    // Shelf Grid
    grid.innerHTML = '';
    if (!data.plays || data.plays.length === 0) {
      grid.innerHTML = '<div class="col-span-full py-16 text-center text-slate-400">No games logged yet. Click "Log a Played Game" to build your shelf!</div>';
      return;
    }

    data.plays.forEach(p => {
      const card = document.createElement('div');
      card.className = "game-card glass-panel rounded-2xl p-4 flex flex-col justify-between border border-white/10 glow-card relative overflow-hidden group";
      
      card.innerHTML = `
        <div>
          <div class="relative aspect-[4/3] rounded-xl overflow-hidden bg-slate-950 mb-3 cursor-pointer" onclick="openGameModal(${p.bgg_id})">
            <img src="${p.image_path || '/static/images/placeholder.jpg'}" alt="${p.name}" class="w-full h-full object-cover">
            <div class="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-lg bg-amber-500 text-slate-950 text-xs font-black shadow-lg flex items-center space-x-1">
              <span>⭐ ${p.rating} / 10</span>
            </div>
            ${p.has_video ? `
            <div class="absolute top-2.5 right-2.5 px-2 py-1 rounded-lg bg-purple-600/90 text-white text-[11px] font-bold">
              <span>Video</span>
            </div>` : ''}
          </div>

          <h4 class="font-extrabold text-white text-base leading-snug cursor-pointer group-hover:text-amber-400 transition line-clamp-1" onclick="openGameModal(${p.bgg_id})">${p.name}</h4>
          
          ${p.notes ? `
          <p class="text-xs text-slate-300 italic mt-2 line-clamp-2 bg-slate-900/60 p-2 rounded-lg border border-white/5">"${p.notes}"</p>
          ` : ''}
        </div>

        <div class="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs">
          <button onclick="openLogPlayModal(${p.bgg_id}, '${escapeQuote(p.name)}')" class="text-amber-400 hover:text-amber-300 font-semibold flex items-center space-x-1">
            <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
            <span>Edit</span>
          </button>
          <button onclick="deletePlay(${p.bgg_id})" class="text-rose-400 hover:text-rose-300 font-semibold flex items-center space-x-1">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            <span>Remove</span>
          </button>
        </div>
      `;
      grid.appendChild(card);
    });
    lucide.createIcons();
  } catch (e) {
    grid.innerHTML = `<div class="col-span-full py-16 text-center text-rose-400">Failed to load shelf: ${e.message}</div>`;
  }
}

async function deletePlay(bggId) {
  if (!state.currentUser) {
    openAuthModal('login');
    showToast("Please sign in to manage your shelf", true);
    return;
  }
  if (!confirm("Remove this game from your shelf?")) return;
  try {
    const res = await fetch(`/api/users/${state.activeUser}/plays/${bggId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${state.authToken}`
      }
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to remove play");
    }
    showToast("Removed game from your shelf");
    loadUserShelf();
  } catch (e) {
    showToast(e.message || "Failed to remove game", true);
  }
}

// ==========================================
// VIEW 4: MANIM VIDEO STUDIO
// ==========================================
async function loadStudioGame() {
  const select = document.getElementById('studio-game-select');
  const bggId = parseInt(select.value, 10);
  const codeArea = document.getElementById('studio-code-editor');
  const statusEl = document.getElementById('studio-status-text');
  const videoPlayer = document.getElementById('studio-video-player');

  codeArea.value = "# Loading script...";
  statusEl.textContent = "Loading...";

  try {
    const res = await fetch(`/api/manim-code/${bggId}`);
    const data = await res.json();
    codeArea.value = data.code;

    // Check video status
    const statusRes = await fetch(`/api/video-status/${bggId}`);
    const statusData = await statusRes.json();
    
    if (statusData.status === 'ready' && statusData.video_url) {
      videoPlayer.src = statusData.video_url;
      videoPlayer.load();
      statusEl.textContent = "Ready";
      statusEl.className = "text-xs text-emerald-400 font-bold";
    } else {
      videoPlayer.src = "";
      statusEl.textContent = "Not made yet";
      statusEl.className = "text-xs text-slate-400";
    }
  } catch (e) {
    codeArea.value = `# Error: ${e.message}`;
    statusEl.textContent = "Error";
  }
}

async function triggerStudioRender() {
  const select = document.getElementById('studio-game-select');
  const bggId = parseInt(select.value, 10);
  const code = document.getElementById('studio-code-editor').value;
  const statusEl = document.getElementById('studio-status-text');
  const btn = document.getElementById('studio-render-btn');

  btn.disabled = true;
  statusEl.textContent = "Making video...";
  statusEl.className = "text-xs text-amber-400 font-bold animate-pulse";

  try {
    const res = await fetch(`/api/custom-manim-render/${bggId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: code, quality: 'm' })
    });
    const data = await res.json();

    // Poll status
    const pollInterval = setInterval(async () => {
      const sRes = await fetch(`/api/video-status/${bggId}`);
      const sData = await sRes.json();
      if (sData.status === 'ready') {
        clearInterval(pollInterval);
        btn.disabled = false;
        statusEl.textContent = "Done!";
        statusEl.className = "text-xs text-emerald-400 font-bold";
        const videoPlayer = document.getElementById('studio-video-player');
        videoPlayer.src = `${sData.video_url}?t=${Date.now()}`;
        videoPlayer.load();
        videoPlayer.play();
        showToast("Video ready!");
      } else if (sData.status === 'error') {
        clearInterval(pollInterval);
        btn.disabled = false;
        statusEl.textContent = `Render Failed: ${sData.error}`;
        statusEl.className = "text-xs text-rose-400 font-bold";
      }
    }, 2000);

  } catch (e) {
    btn.disabled = false;
    statusEl.textContent = `Error: ${e.message}`;
  }
}

// ==========================================
// MODAL: GAME DETAIL & EMBEDDED MANIM PLAYER
// ==========================================
async function openGameModal(bggId) {
  const modal = document.getElementById('game-modal');
  const content = document.getElementById('modal-content');
  modal.classList.remove('hidden');
  content.innerHTML = '<div class="py-20 text-center text-slate-400 font-semibold">Loading...</div>';

  try {
    const res = await fetch(`/api/games/${bggId}`);
    const g = await res.json();
    state.currentGame = g;

    const weightVal = (g.game_weight || 0).toFixed(1);
    const weightDesc = weightVal < 2.0 ? 'Light Strategy' : weightVal < 3.2 ? 'Medium Strategy' : 'Heavy Strategy';

    content.innerHTML = `
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/10">
        <div>
          <div class="flex items-center space-x-2">
            <h2 class="text-2xl sm:text-3xl font-extrabold text-white">${g.name}</h2>
            <span class="text-lg text-slate-400 font-semibold">(${g.year_published || 'N/A'})</span>
          </div>
          <div class="flex flex-wrap items-center gap-2 mt-2 text-xs">
            <span class="px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
              ★ ${g.bayes_avg_rating ? g.bayes_avg_rating.toFixed(2) : 'N/A'} Geek Rating
            </span>
            <span class="px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-bold">
              ${g.num_ratings ? g.num_ratings.toLocaleString() : 0} Gamer Votes
            </span>
            <span class="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
              Weight: ${weightVal} / 5 (${weightDesc})
            </span>
          </div>
        </div>
        <button onclick="openLogPlayModal(${g.bgg_id}, '${escapeQuote(g.name)}')" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm shadow-lg shadow-amber-500/20 flex items-center space-x-1.5 transition self-start sm:self-auto">
          <i data-lucide="plus-circle" class="w-4 h-4"></i>
          <span>Log / Rate Game</span>
        </button>
      </div>

      <!-- Main Columns -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <!-- Left: Image & Specs -->
        <div class="lg:col-span-4 space-y-4">
          <div class="rounded-2xl overflow-hidden bg-slate-950 border border-white/10 shadow-2xl">
            <img src="${g.image_path || '/static/images/placeholder.jpg'}" alt="${g.name}" class="w-full object-cover">
          </div>

          <div class="glass-panel p-4 rounded-2xl border border-white/5 space-y-3 text-xs">
            <div class="flex justify-between py-1 border-b border-white/5">
              <span class="text-slate-400">Players</span>
              <span class="font-bold text-slate-100">${g.min_players}-${g.max_players} (Best: ${g.best_players || 'Flexible'})</span>
            </div>
            <div class="flex justify-between py-1 border-b border-white/5">
              <span class="text-slate-400">Playtime</span>
              <span class="font-bold text-slate-100">${g.mfg_playtime || 45} mins</span>
            </div>
            <div class="flex justify-between py-1 border-b border-white/5">
              <span class="text-slate-400">Designer(s)</span>
              <span class="font-bold text-slate-100 truncate max-w-[160px]">${g.designers || 'Unknown'}</span>
            </div>
            <div class="flex justify-between py-1 border-b border-white/5">
              <span class="text-slate-400">Publisher(s)</span>
              <span class="font-bold text-slate-100 truncate max-w-[160px]">${g.publishers || 'Various'}</span>
            </div>
          </div>
        </div>

        <!-- Right: Video & Rules -->
        <div class="lg:col-span-8 space-y-6">
          
          <!-- Video Section -->
          <div class="glass-panel p-5 rounded-2xl border border-purple-500/30 space-y-4 bg-slate-950/80">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <div class="w-8 h-8 rounded-lg bg-purple-600/20 text-purple-400 flex items-center justify-center font-bold">
                  <i data-lucide="clapperboard" class="w-4 h-4"></i>
                </div>
                <div>
                  <h3 class="text-sm font-bold text-white">Video</h3>
                  <p class="text-[11px] text-purple-300">How to play</p>
                </div>
              </div>
              <button onclick="jumpToStudioWithGame(${g.bgg_id})" class="text-xs text-purple-400 hover:text-purple-300 flex items-center space-x-1 font-semibold">
                <i data-lucide="code" class="w-3.5 h-3.5"></i>
                <span>Script</span>
              </button>
            </div>

            <!-- Video Player -->
            <div id="modal-video-wrapper" class="aspect-video rounded-xl bg-slate-900 border border-white/10 overflow-hidden relative flex items-center justify-center">
              ${g.has_video ? `
                <video id="modal-video-player" src="${g.video_url}" controls class="w-full h-full object-contain"></video>
              ` : `
                <div class="text-center p-6 space-y-3">
                  <div class="w-12 h-12 rounded-full bg-purple-600/20 text-purple-400 flex items-center justify-center mx-auto">
                    <i data-lucide="play" class="w-6 h-6"></i>
                  </div>
                  <h4 class="text-base font-bold text-white">No Video Yet</h4>
                  <p class="text-xs text-slate-400 max-w-sm">Make a video for ${g.name}.</p>
                  <button id="modal-render-btn" onclick="generateVideoForModal(${g.bgg_id})" class="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-lg shadow-purple-600/30 flex items-center space-x-2 mx-auto transition">
                    <i data-lucide="play" class="w-3.5 h-3.5"></i>
                    <span>Make Video</span>
                  </button>
                  <div id="modal-render-progress" class="hidden text-xs text-amber-400 font-bold animate-pulse pt-2">
                    Making video...
                  </div>
                </div>
              `}
            </div>

            ${g.has_video ? `
            <!-- Chapter Markers -->
            <div class="flex items-center gap-2 overflow-x-auto text-[11px] pt-1">
              <span class="text-slate-400 font-semibold mr-1">Parts:</span>
              <button onclick="seekVideo(0)" class="chapter-pill px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 whitespace-nowrap">Intro</button>
              <button onclick="seekVideo(15)" class="chapter-pill px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 whitespace-nowrap">Goal</button>
              <button onclick="seekVideo(35)" class="chapter-pill px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 whitespace-nowrap">Setup</button>
              <button onclick="seekVideo(75)" class="chapter-pill px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 whitespace-nowrap">Rules</button>
              <button onclick="seekVideo(115)" class="chapter-pill px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 whitespace-nowrap">Turn</button>
              <button onclick="seekVideo(165)" class="chapter-pill px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 whitespace-nowrap">Tips</button>
              <button onclick="seekVideo(210)" class="chapter-pill px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 whitespace-nowrap">Win</button>
            </div>
            ` : ''}
          </div>

          <!-- Components Section -->
          ${g.components ? `
          <div class="space-y-2">
            <h4 class="text-sm font-extrabold text-slate-200 flex items-center space-x-1.5">
              <i data-lucide="package" class="w-4 h-4 text-amber-400"></i>
              <span>Components</span>
            </h4>
            <div class="flex flex-wrap gap-1.5 text-xs">
              ${g.components.split(';').map(c => c.trim()).filter(c => c).map(c => `
                <span class="px-2.5 py-1 rounded-lg bg-slate-900 border border-white/10 text-slate-300 font-medium">${c}</span>
              `).join('')}
            </div>
          </div>
          ` : ''}

          <!-- How to Play Section -->
          ${g.how_to_play ? `
          <div class="space-y-2">
            <h4 class="text-sm font-extrabold text-slate-200 flex items-center space-x-1.5">
              <i data-lucide="book-open" class="w-4 h-4 text-cyan-400"></i>
              <span>How to Play</span>
            </h4>
            <div class="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-4 rounded-xl border border-white/10 whitespace-pre-line">
              ${g.how_to_play}
            </div>
          </div>
          ` : ''}

          <!-- Description / Synopsis -->
          <div class="space-y-2">
            <h4 class="text-sm font-extrabold text-slate-200">About</h4>
            <div class="text-xs text-slate-300 leading-relaxed max-h-48 overflow-y-auto pr-2 bg-slate-900/50 p-4 rounded-xl border border-white/5 whitespace-pre-line">
              ${g.description || 'No description available for this title.'}
            </div>
          </div>

          <!-- Gameplay Mechanics & Themes Tags -->
          <div class="space-y-3">
            <h4 class="text-sm font-extrabold text-slate-200">Tags</h4>
            <div class="flex flex-wrap gap-2 text-xs">
              ${(g.mechanics || '').split(';').map(m => m.trim()).filter(m => m).map(m => `
                <span class="px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20 font-medium">${m}</span>
              `).join('')}
              ${(g.themes || '').split(';').map(t => t.trim()).filter(t => t).map(t => `
                <span class="px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-medium">${t}</span>
              `).join('')}
            </div>
          </div>

          <!-- STRATEGY PLAYBOOK & READING SECTION -->
          <div class="space-y-4 pt-2">
            <div class="flex items-center justify-between pb-2 border-b border-amber-500/20">
              <h4 class="text-sm font-extrabold text-amber-400 flex items-center space-x-2">
                <i data-lucide="crown" class="w-4 h-4"></i>
                <span>Winning Strategies</span>
              </h4>
              ${g.submitted_by ? `
                <span class="px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[10px] font-bold">
                  Community Verified (@${g.submitted_by})
                </span>
              ` : ''}
            </div>

            ${g.winning_strategies ? `
            <!-- Catalog Winning Strategy -->
            <div class="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-2">
              <div class="flex items-center space-x-2 text-amber-300 font-bold text-xs">
                <i data-lucide="compass" class="w-3.5 h-3.5 text-amber-400"></i>
                <span>Tactical Playbook & Strategy</span>
              </div>
              <p class="text-xs text-slate-200 leading-relaxed whitespace-pre-line bg-slate-950/60 p-3 rounded-xl border border-white/5">
                ${g.winning_strategies}
              </p>
            </div>
            ` : ''}

            ${g.how_i_won ? `
            <!-- How I Won Playbook -->
            <div class="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-2">
              <div class="flex items-center space-x-2 text-amber-300 font-bold text-xs">
                <i data-lucide="trophy" class="w-3.5 h-3.5 text-amber-400"></i>
                <span>The Victor's Playbook: How I Won My Last Match</span>
              </div>
              <p class="text-xs text-slate-200 leading-relaxed whitespace-pre-line italic bg-slate-950/60 p-3 rounded-xl border border-white/5">
                "${g.how_i_won}"
              </p>
            </div>
            ` : ''}

            ${g.winning_tips ? `
            <!-- Winning Tips -->
            <div class="p-4 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 space-y-2">
              <div class="flex items-center space-x-2 text-cyan-300 font-bold text-xs">
                <i data-lucide="lightbulb" class="w-3.5 h-3.5 text-cyan-400"></i>
                <span>Expert Winning Tips & Tactical Nuance</span>
              </div>
              <p class="text-xs text-slate-200 leading-relaxed whitespace-pre-line bg-slate-950/60 p-3 rounded-xl border border-white/5">
                ${g.winning_tips}
              </p>
            </div>
            ` : ''}

            <!-- Tactical Strategic Reading Guide -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              <div class="glass-panel p-3.5 rounded-xl border border-white/10 space-y-1.5">
                <div class="flex items-center space-x-1.5 text-xs font-bold text-emerald-400">
                  <i data-lucide="play" class="w-3.5 h-3.5"></i>
                  <span>1. Opening Economy</span>
                </div>
                <p class="text-[11px] text-slate-300 leading-normal">
                  Prioritize income ramp and early engine anchors. Avoid low-value immediate points; build recurring production.
                </p>
              </div>

              <div class="glass-panel p-3.5 rounded-xl border border-white/10 space-y-1.5">
                <div class="flex items-center space-x-1.5 text-xs font-bold text-cyan-400">
                  <i data-lucide="cpu" class="w-3.5 h-3.5"></i>
                  <span>2. Mid-Game Synergies</span>
                </div>
                <p class="text-[11px] text-slate-300 leading-normal">
                  Draft cards with cost discounts and synergistic tag multipliers. Watch opponent positions to deny key spaces.
                </p>
              </div>

              <div class="glass-panel p-3.5 rounded-xl border border-white/10 space-y-1.5">
                <div class="flex items-center space-x-1.5 text-xs font-bold text-amber-400">
                  <i data-lucide="flag" class="w-3.5 h-3.5"></i>
                  <span>3. Endgame Conversion</span>
                </div>
                <p class="text-[11px] text-slate-300 leading-normal">
                  Pivot completely from engine building into raw Victory Points 2 rounds before triggers. Calculate opponent scoring potential.
                </p>
              </div>
            </div>
          </div>

          <!-- Similar Games Carousel -->
          ${g.similar_games && g.similar_games.length > 0 ? `
          <div class="space-y-3 pt-2">
            <h4 class="text-sm font-extrabold text-slate-200 flex items-center space-x-1.5">
              <i data-lucide="layers" class="w-4 h-4 text-cyan-400"></i>
              <span>Similar Games You Might Like</span>
            </h4>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              ${g.similar_games.map(sg => `
                <div class="bg-slate-900/80 p-2.5 rounded-xl border border-white/5 hover:border-cyan-500/40 cursor-pointer transition flex items-center space-x-2.5" onclick="openGameModal(${sg.bgg_id})">
                  <img src="${sg.image_path || '/static/images/placeholder.jpg'}" class="w-10 h-10 object-cover rounded-lg">
                  <div class="overflow-hidden">
                    <div class="text-xs font-bold text-white truncate">${sg.name}</div>
                    <div class="text-[10px] text-cyan-400">⭐ ${(sg.bayes_avg_rating||0).toFixed(1)}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
          ` : ''}

        </div>
      </div>
    `;
    lucide.createIcons();
  } catch (e) {
    content.innerHTML = `<div class="py-20 text-center text-rose-400">Error loading game details: ${e.message}</div>`;
  }
}

function closeGameModal() {
  const modal = document.getElementById('game-modal');
  modal.classList.add('hidden');
  const video = document.getElementById('modal-video-player');
  if (video) video.pause();
  if (state.activeVideoPollInterval) clearInterval(state.activeVideoPollInterval);
}

function seekVideo(seconds) {
  const video = document.getElementById('modal-video-player');
  if (video) {
    video.currentTime = seconds;
    video.play();
  }
}

async function generateVideoForModal(bggId) {
  const btn = document.getElementById('modal-render-btn');
  const prog = document.getElementById('modal-render-progress');
  btn.disabled = true;
  btn.classList.add('opacity-50');
  prog.classList.remove('hidden');

  try {
    const userParam = state.currentUser ? `&username=${encodeURIComponent(state.activeUser)}` : '';
    await fetch(`/api/generate-video/${bggId}?quality=m${userParam}`, { method: 'POST' });

    state.activeVideoPollInterval = setInterval(async () => {
      const res = await fetch(`/api/video-status/${bggId}`);
      const data = await res.json();
      if (data.status === 'ready') {
        clearInterval(state.activeVideoPollInterval);
        showToast("Video ready!");
        openGameModal(bggId); // reload modal with video ready
      } else if (data.status === 'error') {
        clearInterval(state.activeVideoPollInterval);
        prog.textContent = `Render error: ${data.error}`;
        prog.classList.replace('text-amber-400', 'text-rose-400');
      }
    }, 2000);
  } catch (e) {
    prog.textContent = `Error: ${e.message}`;
  }
}

function jumpToStudioWithGame(bggId) {
  closeGameModal();
  navigate('studio');
  const select = document.getElementById('studio-game-select');
  // Check if option exists, otherwise add it
  let exists = false;
  for (let i = 0; i < select.options.length; i++) {
    if (parseInt(select.options[i].value, 10) === bggId) {
      select.selectedIndex = i;
      exists = true;
      break;
    }
  }
  if (!exists && state.currentGame) {
    const opt = document.createElement('option');
    opt.value = bggId;
    opt.textContent = `${state.currentGame.name} (ID: ${bggId})`;
    select.appendChild(opt);
    select.value = bggId;
  }
  loadStudioGame();
}

// ==========================================
// MODAL: LOG PLAY
// ==========================================
function openLogPlayModal(bggId, gameTitle) {
  if (!state.currentUser) {
    openAuthModal('signup');
    showToast("Please create an account or sign in to log plays", true);
    return;
  }
  state.activeLogGameId = bggId;
  document.getElementById('log-modal-game-title').textContent = gameTitle || `Game #${bggId}`;
  document.getElementById('log-notes-input').value = '';
  document.getElementById('log-modal').classList.remove('hidden');
}

function closeLogModal() {
  document.getElementById('log-modal').classList.add('hidden');
}

function updateLogRatingVal(val) {
  document.getElementById('log-rating-val').textContent = val;
}

async function submitPlayLog() {
  if (!state.currentUser) {
    closeLogModal();
    openAuthModal('signup');
    showToast("Please sign in or create an account to record plays", true);
    return;
  }
  if (!state.activeLogGameId) return;
  const rating = parseFloat(document.getElementById('log-rating-slider').value);
  const notes = document.getElementById('log-notes-input').value.trim();

  try {
    const res = await fetch(`/api/users/${state.activeUser}/plays`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${state.authToken}`
      },
      body: JSON.stringify({
        bgg_id: state.activeLogGameId,
        rating: rating,
        played: 1,
        notes: notes
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to log play");
    }
    const data = await res.json();
    closeLogModal();
    showToast(`Logged play for ${state.activeUser}!`);
    if (state.currentView === 'shelf') loadUserShelf();
    if (state.currentView === 'recommender') loadRecommendations();
  } catch (e) {
    showToast(e.message || "Failed to save play log", true);
  }
}

// ==========================================
// UTILITIES
// ==========================================
function escapeQuote(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'");
}

function showToast(msg, isError = false) {
  const toast = document.getElementById('toast');
  const text = document.getElementById('toast-msg');
  const icon = document.getElementById('toast-icon');

  text.textContent = msg;
  if (isError) {
    icon.className = "w-5 h-5 text-rose-400";
    toast.className = "fixed bottom-5 right-5 z-50 transform translate-y-0 opacity-100 transition-all duration-300 glass-panel px-4 py-3 rounded-2xl border border-rose-500/30 shadow-2xl flex items-center space-x-3";
  } else {
    icon.className = "w-5 h-5 text-emerald-400";
    toast.className = "fixed bottom-5 right-5 z-50 transform translate-y-0 opacity-100 transition-all duration-300 glass-panel px-4 py-3 rounded-2xl border border-emerald-500/30 shadow-2xl flex items-center space-x-3";
  }

  setTimeout(() => {
    toast.className = "fixed bottom-5 right-5 z-50 transform translate-y-24 opacity-0 transition-all duration-300 glass-panel px-4 py-3 rounded-2xl border border-white/10 shadow-2xl flex items-center space-x-3";
  }, 3500);
}

// ==========================================
// vLLM MODEL HOT-SWAP CONTROLLER
// ==========================================
async function loadLLMConfig() {
  try {
    const res = await fetch('/api/llm/config');
    const cfg = await res.json();
    updateLLMNavbarBadge(cfg);
  } catch (e) {
    console.warn("Could not load LLM config:", e);
  }
}

function updateLLMNavbarBadge(cfg) {
  const nameEl = document.getElementById('llm-active-model-name');
  const dotEl = document.getElementById('llm-status-dot');
  if (!nameEl) return;

  const rawModel = cfg.model_name || 'Procedural Engine';
  const shortName = rawModel.split('/').pop();
  nameEl.textContent = shortName;

  if (!cfg.enabled) {
    dotEl.className = "w-2 h-2 rounded-full bg-slate-500";
    nameEl.textContent = "Offline (Procedural)";
  } else {
    dotEl.className = "w-2 h-2 rounded-full bg-emerald-400";
  }
}

let llmProfiles = null;
let llmActiveProvider = 'zai';

function fillLLMForm(profile) {
  document.getElementById('llm-input-url').value = profile.api_base_url || '';
  document.getElementById('llm-input-model').value = profile.model_name || '';
  document.getElementById('llm-input-key').value = profile.api_key || '';
  document.getElementById('llm-input-temp').value = profile.temperature ?? 0.2;
  document.getElementById('llm-input-tokens').value = profile.max_tokens || 3000;
}

function paintLLMProvider(provider) {
  llmActiveProvider = provider;
  const zaiBtn = document.getElementById('llm-provider-zai');
  const amdBtn = document.getElementById('llm-provider-amd');
  const note = document.getElementById('llm-provider-note');
  const on = 'px-3 py-2 rounded-xl border border-cyan-400/50 bg-cyan-500/15 text-cyan-200 font-bold';
  const off = 'px-3 py-2 rounded-xl border border-white/10 bg-slate-900 text-slate-200 font-bold';
  if (zaiBtn) zaiBtn.className = provider === 'zai' ? on : off;
  if (amdBtn) amdBtn.className = provider === 'amd' ? on : off;
  if (note) {
    note.textContent = provider === 'amd'
      ? 'Gemma-4-31B-IT on AMD Token Factory. Paste the team key (rc-…) when you redeem it. z.ai stays saved.'
      : 'z.ai is the active endpoint. AMD Gemma is saved and ready to switch on.';
  }
}

function stashLLMForm() {
  if (!llmProfiles) return;
  llmProfiles[llmActiveProvider] = {
    ...(llmProfiles[llmActiveProvider] || {}),
    api_base_url: document.getElementById('llm-input-url').value.trim(),
    model_name: document.getElementById('llm-input-model').value.trim(),
    api_key: document.getElementById('llm-input-key').value.trim(),
    temperature: parseFloat(document.getElementById('llm-input-temp').value) || 0.2,
    max_tokens: parseInt(document.getElementById('llm-input-tokens').value, 10) || 3000,
  };
}

function selectLLMProvider(provider) {
  stashLLMForm();
  paintLLMProvider(provider);
  fillLLMForm(llmProfiles[provider] || {});
}

async function openLLMModal() {
  const modal = document.getElementById('llm-modal');
  modal.classList.remove('hidden');

  try {
    const res = await fetch('/api/llm/config');
    const cfg = await res.json();
    llmProfiles = cfg.providers || { zai: cfg, amd: cfg };
    document.getElementById('llm-input-enabled').checked = cfg.enabled !== false;
    paintLLMProvider(cfg.provider || 'zai');
    fillLLMForm(llmProfiles[cfg.provider || 'zai'] || cfg);
    testLLMConnection();
  } catch (e) {
    console.error("Error opening LLM modal:", e);
  }
}

function closeLLMModal() {
  document.getElementById('llm-modal').classList.add('hidden');
}

function setLLMPreset(modelName) {
  document.getElementById('llm-input-model').value = modelName;
}

async function testLLMConnection() {
  const dot = document.getElementById('llm-modal-status-dot');
  const text = document.getElementById('llm-modal-status-text');
  const discDiv = document.getElementById('llm-discovered-models');
  const chipsDiv = document.getElementById('llm-models-chips');
  const countSpan = document.getElementById('llm-available-count');

  dot.className = "w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse";
  text.textContent = "Connecting...";

  try {
    const res = await fetch('/api/llm/test', { method: 'POST' });
    const data = await res.json();

    if (data.connected) {
      dot.className = "w-2.5 h-2.5 rounded-full bg-emerald-400";
      text.textContent = `Online (${data.available_models.length} model(s))`;
      
      if (data.available_models && data.available_models.length > 0) {
        discDiv.classList.remove('hidden');
        chipsDiv.innerHTML = '';
        data.available_models.forEach(m => {
          const btn = document.createElement('button');
          btn.className = "px-2 py-0.5 rounded-md bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 font-mono text-[10px] border border-purple-500/30";
          btn.textContent = m;
          btn.onclick = () => setLLMPreset(m);
          chipsDiv.appendChild(btn);
        });
        countSpan.textContent = `(${data.available_models.length} available)`;
      }
    } else {
      dot.className = "w-2.5 h-2.5 rounded-full bg-rose-500";
      text.textContent = `Offline`;
      discDiv.classList.add('hidden');
      countSpan.textContent = '';
    }
  } catch (e) {
    dot.className = "w-2.5 h-2.5 rounded-full bg-rose-500";
    text.textContent = `Offline: ${e.message}`;
  }
}

async function saveLLMConfig() {
  const url = document.getElementById('llm-input-url').value.trim();
  const model = document.getElementById('llm-input-model').value.trim();
  const temp = parseFloat(document.getElementById('llm-input-temp').value) || 0.2;
  const tokens = parseInt(document.getElementById('llm-input-tokens').value, 10) || 3000;
  const enabled = document.getElementById('llm-input-enabled').checked;

  try {
    const res = await fetch('/api/llm/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: llmActiveProvider,
        api_base_url: url,
        model_name: model,
        api_key: document.getElementById('llm-input-key').value.trim(),
        temperature: temp,
        max_tokens: tokens,
        enabled: enabled
      })
    });
    const data = await res.json();
    if (data.status === 'success') {
      updateLLMNavbarBadge(data.config);
      showToast(`Model set: ${model.split('/').pop()}!`);
      closeLLMModal();
    } else {
      showToast("Error updating configuration", true);
    }
  } catch (e) {
    showToast(`Error: ${e.message}`, true);
  }
}

// ==========================================
// VIEW 5: COMMUNITY SUBMISSIONS & DUPLICATE ENGINE
// ==========================================
let duplicateCheckTimer = null;

function debouncedCheckDuplicate(e) {
  clearTimeout(duplicateCheckTimer);
  const name = e.target.value.trim();
  const indicator = document.getElementById('duplicate-check-indicator');
  const warningBanner = document.getElementById('duplicate-warning-banner');
  const warningText = document.getElementById('duplicate-warning-text');
  const submitBtn = document.getElementById('submit-game-btn');
  const dupIcon = document.getElementById('sub-dup-icon');

  if (!name || name.length < 2) {
    if (indicator) indicator.textContent = '';
    if (warningBanner) warningBanner.classList.add('hidden');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    }
    if (dupIcon) dupIcon.className = "w-4 h-4 absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500";
    return;
  }

  if (dupIcon) dupIcon.className = "w-4 h-4 absolute right-3.5 top-1/2 -translate-y-1/2 text-amber-400 animate-spin";
  if (indicator) {
    indicator.textContent = "Verifying 95k+ catalog for duplicates...";
    indicator.className = "text-[11px] font-semibold text-amber-400";
  }

  duplicateCheckTimer = setTimeout(async () => {
    try {
      const res = await fetch(`/api/games/check-duplicate?name=${encodeURIComponent(name)}`);
      const data = await res.json();

      if (data.is_duplicate) {
        if (dupIcon) dupIcon.className = "w-4 h-4 absolute right-3.5 top-1/2 -translate-y-1/2 text-rose-500";
        if (indicator) {
          indicator.textContent = `❌ Already in Wiki (ID #${data.existing_game?.bgg_id || 'CATALOG'})`;
          indicator.className = "text-[11px] font-bold text-rose-400";
        }
        if (warningBanner && warningText) {
          warningText.textContent = `"${data.existing_game?.name}" (${data.existing_game?.year_published || 'N/A'}) already exists in our 95k catalog! Submitting duplicate game titles is prohibited.`;
          warningBanner.classList.remove('hidden');
        }
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }
      } else {
        if (dupIcon) dupIcon.className = "w-4 h-4 absolute right-3.5 top-1/2 -translate-y-1/2 text-emerald-400";
        if (indicator) {
          indicator.textContent = "✅ Unique verified title - Ready for submission";
          indicator.className = "text-[11px] font-bold text-emerald-400";
        }
        if (warningBanner) warningBanner.classList.add('hidden');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
      }
    } catch (err) {
      if (indicator) {
        indicator.textContent = "Duplicate check offline";
        indicator.className = "text-[11px] text-slate-400";
      }
      if (dupIcon) dupIcon.className = "w-4 h-4 absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500";
    }
  }, 350);
}

async function handleGameSubmission(e) {
  e.preventDefault();

  if (!state.currentUser || !state.authToken) {
    openAuthModal('signup');
    showToast("You must create an account or sign in before submitting games", true);
    return;
  }

  const submitBtn = document.getElementById('submit-game-btn');
  const name = document.getElementById('sub-game-name').value.trim();
  const yearPublished = parseInt(document.getElementById('sub-year').value, 10) || new Date().getFullYear();
  const minPlayers = parseInt(document.getElementById('sub-min-players').value, 10) || 2;
  const maxPlayers = parseInt(document.getElementById('sub-max-players').value, 10) || 4;
  const mfgPlaytime = parseInt(document.getElementById('sub-playtime').value, 10) || 60;
  const gameWeight = parseFloat(document.getElementById('sub-weight').value) || 2.5;
  const categories = document.getElementById('sub-categories').value.trim();
  const mechanics = document.getElementById('sub-mechanics').value.trim();
  const description = document.getElementById('sub-description').value.trim();
  const howIWon = document.getElementById('sub-how-i-won').value.trim();
  const winningTips = document.getElementById('sub-winning-tips').value.trim();

  if (!name) {
    showToast("Please provide a game title", true);
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerHTML = `
    <i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>
    <span>Validating & Publishing to Wiki...</span>
  `;
  lucide.createIcons();

  try {
    const res = await fetch('/api/games/submit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${state.authToken}`
      },
      body: JSON.stringify({
        name: name,
        year_published: yearPublished,
        min_players: minPlayers,
        max_players: maxPlayers,
        mfg_playtime: mfgPlaytime,
        game_weight: gameWeight,
        categories: categories,
        mechanics: mechanics,
        description: description,
        how_i_won: howIWon,
        winning_tips: winningTips
      })
    });

    const data = await res.json();
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <i data-lucide="upload" class="w-4 h-4"></i>
      <span>Publish Game & Winning Strategy to Wiki</span>
    `;
    lucide.createIcons();

    if (!res.ok) {
      showToast(data.detail || "Submission rejected", true);
      const warningBanner = document.getElementById('duplicate-warning-banner');
      const warningText = document.getElementById('duplicate-warning-text');
      if (warningBanner && warningText) {
        warningText.textContent = data.detail || "Submission error";
        warningBanner.classList.remove('hidden');
      }
      return;
    }

    showToast(`🎉 "${data.game.name}" & Winning Strategy successfully added to Aatam Wiki!`);
    document.getElementById('game-submission-form').reset();
    document.getElementById('duplicate-check-indicator').textContent = '';
    const warningBanner = document.getElementById('duplicate-warning-banner');
    if (warningBanner) warningBanner.classList.add('hidden');

    loadCommunitySubmissions();
    openGameModal(data.game.bgg_id);
  } catch (err) {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <i data-lucide="upload" class="w-4 h-4"></i>
      <span>Publish Game & Winning Strategy to Wiki</span>
    `;
    lucide.createIcons();
    showToast(`Submission failed: ${err.message}`, true);
  }
}

async function loadCommunitySubmissions() {
  const listEl = document.getElementById('community-submissions-list');
  if (!listEl) return;

  listEl.innerHTML = '<div class="py-8 text-center text-slate-500 text-xs">Loading community contributions...</div>';

  try {
    const res = await fetch('/api/submissions');
    const data = await res.json();
    const subs = data.submissions || [];

    if (subs.length === 0) {
      listEl.innerHTML = `
        <div class="p-6 rounded-2xl bg-slate-900/40 border border-white/5 text-center space-y-2">
          <i data-lucide="inbox" class="w-6 h-6 text-slate-600 mx-auto"></i>
          <p class="text-xs text-slate-400">No community submissions yet.</p>
          <p class="text-[11px] text-slate-500">Be the first player to publish a new board game and winning playbook!</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    listEl.innerHTML = '';
    subs.slice().reverse().forEach(s => {
      const card = document.createElement('div');
      card.className = "p-4 rounded-2xl glass-panel border border-white/10 hover:border-amber-500/30 transition space-y-2.5";
      card.innerHTML = `
        <div class="flex items-start justify-between gap-2">
          <div>
            <h4 class="font-bold text-white text-sm hover:text-amber-400 cursor-pointer transition line-clamp-1" onclick="openGameModal(${s.bgg_id})">
              ${s.name} <span class="text-xs text-slate-400">(${s.year_published || 'N/A'})</span>
            </h4>
            <div class="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
              <span class="text-amber-400 font-semibold">@${s.submitted_by || 'Anonymous'}</span>
              <span>•</span>
              <span>Weight: ${(s.game_weight || 2.5).toFixed(1)}/5</span>
              <span>•</span>
              <span>${s.min_players}-${s.max_players}p</span>
            </div>
          </div>
          <button onclick="openGameModal(${s.bgg_id})" class="p-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 transition" title="View Game & Rules">
            <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
          </button>
        </div>

        ${s.how_i_won ? `
        <div class="p-2.5 rounded-xl bg-amber-500/5 border border-amber-500/15 text-[11px] text-slate-300">
          <span class="font-bold text-amber-400 block mb-0.5">🏆 How Victor Won:</span>
          <p class="line-clamp-2 italic text-slate-200">"${s.how_i_won}"</p>
        </div>
        ` : ''}

        ${s.winning_tips ? `
        <div class="p-2.5 rounded-xl bg-cyan-500/5 border border-cyan-500/15 text-[11px] text-slate-300">
          <span class="font-bold text-cyan-400 block mb-0.5">💡 Winning Tip:</span>
          <p class="line-clamp-2 text-slate-200">${s.winning_tips}</p>
        </div>
        ` : ''}
      `;
      listEl.appendChild(card);
    });
    lucide.createIcons();
  } catch (err) {
    listEl.innerHTML = `<div class="py-6 text-center text-rose-400 text-xs">Failed to load submissions: ${err.message}</div>`;
  }
}

