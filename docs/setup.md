# Запуск проекта

## Установка репозитория

```bash
git clone <repo_url>
cd <project>
```

---

## Создание .env

Скопируйте пример:

```bash
cp .env_example .env
```

Заполните вашими данными:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_ID=
```

Поле `TELEGAM_ADMIN_IDS` должно заполняться через запятую без пробелов

---

## Установка зависимостей

```bash
pip install -r requirements.txt
```

---

## Запуск бота

Возможно, для работы с `make` надо посмотреть [инструкцию](windows_make.md)

```bash
make run
```

Запустить можно и руками через
```bash
python3 -m main
```

---
