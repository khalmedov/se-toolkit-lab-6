# Task 3: The System Agent - Implementation Plan

## 1. Новый tool: `run_command`

### Описание
Выполняет системные команды на ВМ и возвращает результат.

### Параметры
- `command` (string) - команда для выполнения
- `timeout` (integer, optional) - таймаут в секундах (по умолчанию 10)

### Безопасность
- Запретить опасные команды (rm -rf, sudo, dd, etc.)
- White list разрешенных команд
- Максимальное время выполнения

### Возвращает
- stdout + stderr команды
- Код возврата
- Сообщение об ошибке если команда запрещена

## 2. Обновить system prompt

Добавить инструкции по использованию run_command для:
- Проверки статуса сервисов
- Просмотра логов
- Мониторинга системы

## 3. Agentic loop improvements

- Увеличить макс итераций до 15
- Добавить обработку ошибок команд
- Сохранять историю команд

## 4. Output format

```json
{
  "answer": "Ответ на вопрос",
  "source": "system",
  "tool_calls": [
    {
      "tool": "run_command",
      "args": {"command": "docker ps"},
      "result": "CONTAINER ID   IMAGE   ..."
    }
  ]
}
