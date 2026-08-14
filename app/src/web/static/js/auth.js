document.addEventListener("DOMContentLoaded", () => {
    if (getToken()) {
        window.location.href = "/dashboard";
        return;
    }

    const message = document.querySelector("#auth-message");
    const loginForm = document.querySelector("#login-form");
    const registerForm = document.querySelector("#register-form");

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideMessage(message);
        const submitButton = loginForm.querySelector("button[type='submit']");
        submitButton.disabled = true;
        try {
            const data = await apiRequest(
                "/auth/login",
                {
                    method: "POST",
                    body: JSON.stringify({
                        email: loginForm.email.value,
                        password: loginForm.password.value,
                    }),
                },
                false,
            );
            saveToken(data.access_token);
            window.location.href = "/dashboard";
        } catch (error) {
            showMessage(message, error.message);
        } finally {
            submitButton.disabled = false;
        }
    });

    registerForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideMessage(message);
        const submitButton = registerForm.querySelector("button[type='submit']");
        submitButton.disabled = true;
        try {
            await apiRequest(
                "/auth/register",
                {
                    method: "POST",
                    body: JSON.stringify({
                        email: registerForm.email.value,
                        password: registerForm.password.value,
                    }),
                },
                false,
            );
            loginForm.email.value = registerForm.email.value;
            registerForm.reset();
            showMessage(message, "Регистрация завершена. Теперь войдите в аккаунт.", "success");
        } catch (error) {
            showMessage(message, error.message);
        } finally {
            submitButton.disabled = false;
        }
    });
});
