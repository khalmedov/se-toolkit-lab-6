# Добавим все файлы
git add agent.py tests/test_agent_task2.py AGENT.md

# Закоммитим
git commit -m "feat: implement Task 2 - Documentation Agent

- Add read_file and list_files tools
- Implement agentic loop with max 10 iterations
- Add source field to output
- Add 2 regression tests"

# Запушим
git push origin task-2-documentation-agent

## System Commands (Task 3)

### run_command tool
- Выполняет безопасные системные команды
- Поддерживает таймаут (по умолчанию 10 сек)
- Запрещены опасные команды (rm -rf, sudo, и т.д.)

Примеры:
- `docker ps` - список контейнеров
- `df -h` - свободное место на диске
- `free -m` - использование памяти
