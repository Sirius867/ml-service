document.addEventListener("DOMContentLoaded", async () => {
    if (!requireAuth()) {
        return;
    }

    const pageMessage = document.querySelector("#page-message");
    const balanceElement = document.querySelector("#balance-value");
    const profileElement = document.querySelector("#profile-email");
    const topUpForm = document.querySelector("#top-up-form");
    const predictionForm = document.querySelector("#prediction-form");
    const fileInput = document.querySelector("#features-file");
    const featuresInput = document.querySelector("#features");

    async function loadAccount() {
        try {
            const [profile, balance] = await Promise.all([
                apiRequest("/users/me"),
                apiRequest("/balance"),
            ]);
            profileElement.textContent = profile.email;
            balanceElement.textContent = Number(balance.balance).toFixed(2);
        } catch (error) {
            if (error.status === 401) {
                window.location.href = "/auth";
                return;
            }
            showMessage(pageMessage, error.message);
        }
    }

    fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];
        if (file) {
            featuresInput.value = await file.text();
        }
    });

    topUpForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideMessage(pageMessage);
        try {
            const balance = await apiRequest("/balance/top-up", {
                method: "POST",
                body: JSON.stringify({amount: Number(topUpForm.amount.value)}),
            });
            balanceElement.textContent = Number(balance.balance).toFixed(2);
            topUpForm.reset();
            showMessage(pageMessage, "Баланс пополнен.", "success");
        } catch (error) {
            showMessage(pageMessage, error.message);
        }
    });

    predictionForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideMessage(pageMessage);
        const submitButton = predictionForm.querySelector("button[type='submit']");
        submitButton.disabled = true;
        try {
            const features = JSON.parse(featuresInput.value);
            if (!features || Array.isArray(features) || typeof features !== "object") {
                throw new Error("Введите признаки в виде JSON-объекта.");
            }
            const task = await apiRequest("/predict", {
                method: "POST",
                body: JSON.stringify({
                    model: predictionForm.model.value,
                    features,
                }),
            });
            showMessage(pageMessage, `Задача ${task.task_id} поставлена в очередь.`, "info");
            const result = await waitForResult(task.task_id);
            renderResult(result, features);
            await loadAccount();
        } catch (error) {
            const message = error instanceof SyntaxError
                ? "Не удалось разобрать JSON с признаками."
                : error.message;
            showMessage(pageMessage, message);
        } finally {
            submitButton.disabled = false;
        }
    });

    async function waitForResult(taskId) {
        for (let attempt = 0; attempt < 30; attempt += 1) {
            const result = await apiRequest(`/predict/${taskId}`);
            if (["completed", "failed"].includes(result.status)) {
                return result;
            }
            await new Promise((resolve) => setTimeout(resolve, 1000));
        }
        throw new Error("Время ожидания результата истекло. Проверьте историю позже.");
    }

    function renderResult(result, sourceFeatures) {
        const resultCard = document.querySelector("#prediction-result");
        const invalidNames = new Set(
            result.invalid_data
                .filter((item) => item && item.feature)
                .map((item) => item.feature),
        );
        const processedFeatures = Object.fromEntries(
            Object.entries(sourceFeatures).filter(([name]) => !invalidNames.has(name)),
        );

        document.querySelector("#result-status").textContent = result.status;
        document.querySelector("#result-value").textContent = result.prediction ?? "—";
        document.querySelector("#result-charge").textContent = Number(result.charged_amount).toFixed(2);
        document.querySelector("#processed-data").textContent = JSON.stringify(processedFeatures, null, 2);
        document.querySelector("#invalid-data").textContent = JSON.stringify(result.invalid_data, null, 2);
        resultCard.hidden = false;
    }

    await loadAccount();
});
