## Установка и запуск

### 1. Получение api токена
[bot_father]: https://t.me/BotFather
[bot_father_info]: https://core.telegram.org/bots#botfather

Для начала нужно получить токен у [Bot Father][bot_father].
Информацию про взаимодействие с ним можно найти [здесь][bot_father_info].

### 2. Установка переменных окружения
Для работы нужно установить переменные `MAFIA_API_TOKEN` и `MAFIA_ADMIN`.

Не знаю, как это делается на Windows, но на Linux достаточно прописать
```bash
export MAFIA_API_TOKEN="<your api token>"
export MAFIA_ADMIN="<your tg username>"
```

*В целом можно обойтись и без них, 
если захардкодить значения этих переменных в проект,
но лучше не стоит так делать*

### 3. Запуск проекта
Установить все нужные зависимости можно с помощью
```bash
pip install -r requirements.txt
```

После этого проект готов к запуску. Достаточно использовать команду
```bash
python3 main.py
```
