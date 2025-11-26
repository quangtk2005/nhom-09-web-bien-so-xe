document.addEventListener('DOMContentLoaded', () => {
    
    const showLogin = document.getElementById('show-login');
    const showRegister = document.getElementById('show-register');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    const btnLogin = document.getElementById('btn-login');
    const btnRegister = document.getElementById('btn-register');

    const loginMsg = document.getElementById('login-msg');
    const regMsg = document.getElementById('reg-msg');

    // Chuyển form
    showRegister.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    });

    showLogin.addEventListener('click', (e) => {
        e.preventDefault();
        registerForm.style.display = 'none';
        loginForm.style.display = 'block';
    });

    // Xử lý Đăng nhập
    btnLogin.addEventListener('click', async () => {
        const username = document.getElementById('login-user').value;
        const password = document.getElementById('login-pass').value;

        loginMsg.textContent = 'Đang kiểm tra...';
        
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            loginMsg.textContent = data.message;
            loginMsg.className = 'message success';
            // Đăng nhập thành công, chuyển hướng đến trang app
            window.location.href = '/app';
        } else {
            loginMsg.textContent = data.message;
            loginMsg.className = 'message error';
        }
    });

    // Xử lý Đăng ký
    btnRegister.addEventListener('click', async () => {
        const payload = {
            username: document.getElementById('reg-user').value,
            password: document.getElementById('reg-pass').value,
            owner_name: document.getElementById('reg-name').value,
            phone: document.getElementById('reg-phone').value,
            license_plate: document.getElementById('reg-plate').value,
            vehicle_info: document.getElementById('reg-vehicle').value
        };

        regMsg.textContent = 'Đang xử lý...';
        
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            regMsg.textContent = data.message + " Vui lòng chuyển qua tab đăng nhập.";
            regMsg.className = 'message success';
        } else {
            regMsg.textContent = data.message;
            regMsg.className = 'message error';
        }
    });
});