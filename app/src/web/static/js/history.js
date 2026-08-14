document.addEventListener("DOMContentLoaded", async () => {
    if (!requireAuth()) {
        return;
    }

    const message = document.querySelector("#history-message");
    try {
        const [predictions, transactions] = await Promise.all([
            apiRequest("/history/predictions"),
            apiRequest("/history/transactions"),
        ]);
        renderPredictions(predictions);
        renderTransactions(transactions);
    } catch (error) {
        if (error.status === 401) {
            window.location.href = "/auth";
            return;
        }
        showMessage(message, error.message);
    }
});

function renderPredictions(items) {
    const body = document.querySelector("#predictions-body");
    const empty = document.querySelector("#predictions-empty");
    empty.hidden = items.length > 0;
    items.forEach((item) => {
        const row = document.createElement("tr");
        addCell(row, formatDate(item.created_at));
        addCell(row, item.model_code);
        addCell(row, JSON.stringify(item.input_data));
        addCell(row, item.prediction);
        addCell(row, JSON.stringify(item.invalid_data));
        addCell(row, Number(item.charged_amount).toFixed(2));
        addCell(row, item.status);
        body.appendChild(row);
    });
}

function renderTransactions(items) {
    const body = document.querySelector("#transactions-body");
    const empty = document.querySelector("#transactions-empty");
    empty.hidden = items.length > 0;
    items.forEach((item) => {
        const row = document.createElement("tr");
        addCell(row, formatDate(item.created_at));
        addCell(row, item.transaction_type === "deposit" ? "Пополнение" : "Списание");
        addCell(row, Number(item.amount).toFixed(2));
        addCell(row, item.request_id);
        addCell(row, "Выполнено");
        body.appendChild(row);
    });
}
