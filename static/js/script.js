function toggleForms() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toggleBtn = document.getElementById('toggleBtn');

    // Alternar clases entre los formularios
    loginForm.classList.toggle('active');
    loginForm.classList.toggle('hidden');
    registerForm.classList.toggle('active');
    registerForm.classList.toggle('hidden');

    // Cambiar el texto del botón
    if (toggleBtn.textContent === 'Go to Register') {
        toggleBtn.textContent = 'Go to Login';
    } else {
        toggleBtn.textContent = 'Go to Register';
    }
}
