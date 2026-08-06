from .models import AdminUser, AverageValueModel, MLTask, RequestHistory, User


def main() -> None:
    user = User("user@example.com", "saved_password_hash")
    admin = AdminUser("admin@example.com", "admin_password_hash")
    model = AverageValueModel(
        name="Average value",
        description="Вычисляет среднее значение числовых данных",
        prediction_cost=10.0,
    )

    deposit = admin.top_up_user(user, 100.0)
    task = MLTask(user, model, [10, 20, "ошибка", 30])
    history = RequestHistory(user)

    debit = task.run()
    history.add(task)

    print(f"Пополнение: {deposit.amount}")
    print(f"Результат: {task.result.prediction}")
    print(f"Ошибочные данные: {task.result.invalid_data}")
    print(f"Списано: {debit.amount}")
    print(f"Баланс: {user.balance}")
    print(f"Записей в истории: {len(history.get_all())}")


if __name__ == "__main__":
    main()
