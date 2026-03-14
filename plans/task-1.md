# Task 1: Call an LLM from Code - Implementation Plan

## 1. LLM Provider Choice
- **Provider**: OpenRouter
- **Model**: `arcee-ai/trinity-large-preview:free`
- **Why**: Бесплатно, работает из РФ, не требует кредитной карты, уже настроено и проверено

## 2. Architecture
- Простой CLI на Python
- Читает вопрос из аргументов командной строки
- Загружает конфигурацию из `.env.agent.secret`
- Отправляет запрос к OpenRouter API
- Выводит JSON с полями `answer` и `tool_calls`

## 3. Implementation Steps
1. Создать `agent.py` в корне проекта
2. Использовать `python-dotenv` для загрузки `.env.agent.secret`
3. Реализовать функцию `call_llm(question)` с запросом к API
4. Парсить ответ и форматировать как JSON
5. Весь debug вывод отправлять в stderr
6. Таймаут 60 секунд

## 4. Testing
- Один regression test в `tests/test_agent.py`
- Проверяет запуск `agent.py` как подпроцесс
- Проверяет наличие полей `answer` и `tool_calls` в JSON ответе
