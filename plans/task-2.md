# Task 2: The Documentation Agent - Implementation Plan

## 1. Tools Implementation

### `read_file(path)`
- Читает файл из репозитория
- Проверка безопасности: запретить `..`, разрешить только пути внутри проекта
- Возвращает содержимое или ошибку

### `list_files(path)`
- Списывает файлы и директории
- Проверка безопасности: запретить выход за пределы проекта
- Возвращает список через newline

## 2. Function Calling Schemas
```python
read_file_schema = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read contents of a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to project root"}
            },
            "required": ["path"]
        }
    }
}
