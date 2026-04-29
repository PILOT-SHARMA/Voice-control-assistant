// Google Sign-In System (Demo Mode for College Project)
let currentUser = null;

function initAuth() {
    const saved = localStorage.getItem('va_user');
    if (saved) {
        currentUser = JSON.parse(saved);
        updateAuthUI(currentUser);
    }
}

function updateAuthUI(user) {
    const authSection = document.getElementById('authSection');
    if (!authSection) return;
    if (user) {
        const name = user.name || 'User';
        const email = user.email || '';
        const photo = user.photo || '';
        const avatarUrl = photo || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(name) + '&background=1a2a4a&color=4285f4&size=64&bold=true';
        authSection.innerHTML = `
            <div class="user-profile">
                <img class="user-avatar" src="${avatarUrl}" alt="avatar" referrerpolicy="no-referrer" onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=1a2a4a&color=4285f4&size=64'">
                <div class="user-info">
                    <div class="user-name">${name}</div>
                    <div class="user-email">${email}</div>
                </div>
            </div>
            <button class="signout-btn" onclick="signOutUser()">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
                Sign Out
            </button>`;
    } else {
        authSection.innerHTML = `
            <button class="google-btn" onclick="signInWithGoogle()">
                <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
                Sign in with Google
            </button>`;
    }
}

function signInWithGoogle() {
    // Show a sign-in modal
    const modal = document.createElement('div');
    modal.id = 'signInModal';
    modal.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,.7);backdrop-filter:blur(8px);z-index:10000;display:flex;align-items:center;justify-content:center;animation:fadeIn .3s ease';
    modal.innerHTML = `
        <div style="background:#1a1a2e;border:1px solid #2a2a4a;border-radius:16px;padding:32px;width:360px;max-width:90vw;box-shadow:0 20px 60px rgba(0,0,0,.5);animation:scaleIn .3s cubic-bezier(.16,1,.3,1)">
            <div style="text-align:center;margin-bottom:24px">
                <svg width="40" height="40" viewBox="0 0 48 48" style="margin-bottom:12px"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
                <h2 style="color:#e8eaed;font-size:20px;font-weight:700;margin:0 0 4px">Sign in with Google</h2>
                <p style="color:#888;font-size:13px;margin:0">Enter your details to continue</p>
            </div>
            <form id="signInForm" onsubmit="handleSignIn(event)">
                <div style="margin-bottom:14px">
                    <label style="color:#aaa;font-size:12px;font-weight:600;display:block;margin-bottom:6px">Full Name</label>
                    <input type="text" id="signInName" required placeholder="e.g. Arpit Sharma" 
                        style="width:100%;padding:10px 14px;background:#111;border:1px solid #333;border-radius:8px;color:#fff;font-size:14px;font-family:Inter,sans-serif;outline:none;box-sizing:border-box;transition:border .2s"
                        onfocus="this.style.borderColor='#4285f4'" onblur="this.style.borderColor='#333'">
                </div>
                <div style="margin-bottom:20px">
                    <label style="color:#aaa;font-size:12px;font-weight:600;display:block;margin-bottom:6px">Email</label>
                    <input type="email" id="signInEmail" required placeholder="e.g. arpit@gmail.com"
                        style="width:100%;padding:10px 14px;background:#111;border:1px solid #333;border-radius:8px;color:#fff;font-size:14px;font-family:Inter,sans-serif;outline:none;box-sizing:border-box;transition:border .2s"
                        onfocus="this.style.borderColor='#4285f4'" onblur="this.style.borderColor='#333'">
                </div>
                <button type="submit" style="width:100%;padding:12px;background:linear-gradient(135deg,#4285f4,#7c4dff);border:none;border-radius:10px;color:#fff;font-size:14px;font-weight:600;cursor:pointer;font-family:Inter,sans-serif;transition:all .3s;box-shadow:0 4px 15px rgba(66,133,244,.3)"
                    onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(66,133,244,.4)'"
                    onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(66,133,244,.3)'">
                    ✨ Sign In
                </button>
            </form>
            <button onclick="closeSignInModal()" style="position:absolute;top:16px;right:16px;background:none;border:none;color:#666;cursor:pointer;font-size:18px;padding:4px 8px;border-radius:6px;transition:all .2s" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='#666'">✕</button>
        </div>`;
    modal.querySelector('div').style.position = 'relative';
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeSignInModal(); });
    document.getElementById('signInName').focus();
}

function handleSignIn(e) {
    e.preventDefault();
    const name = document.getElementById('signInName').value.trim();
    const email = document.getElementById('signInEmail').value.trim();
    if (!name || !email) return;

    const user = { name, email, photo: '' };
    localStorage.setItem('va_user', JSON.stringify(user));
    currentUser = user;
    updateAuthUI(user);
    closeSignInModal();
    showToast('Welcome, ' + name + '! 🎉', 'success');
}

function closeSignInModal() {
    const modal = document.getElementById('signInModal');
    if (modal) {
        modal.style.opacity = '0';
        modal.style.transition = 'opacity .2s';
        setTimeout(() => modal.remove(), 200);
    }
}

function signOutUser() {
    localStorage.removeItem('va_user');
    currentUser = null;
    updateAuthUI(null);
    showToast('Signed out successfully 👋', 'info');
}

document.addEventListener('DOMContentLoaded', initAuth);
