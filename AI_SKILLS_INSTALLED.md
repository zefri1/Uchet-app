# Установленные AI Agent Skills

В данном файле представлен список установленных навыков (skills) для агента Antigravity, предназначенных для поиска багов, ревью кода, тестирования бизнес-логики и автоматизации тестирования.

## Текущая среда
Формат навыков: **Antigravity (AGY)**
Путь установки: `C:\Users\Alexey\Documents\ук\.antigravity\skills`

## Список навыков

### 1. `bug-hunter`
* **Источник**: `codexstar69/bug-hunter/skills/hunter`
* **Назначение**: Поиск уязвимостей, багов в бизнес-логике, ошибок во время выполнения (edge cases testing, bug hunting).
* **Пример использования**:
  ```text
  Запусти bug-hunter для анализа файла app/services/calculations.py и найди потенциальные ошибки при расчетах с плавающей точкой.
  ```

### 2. `qa-test-planner`
* **Источник**: `fugazi/test-automation-skills-agents/skills/qa-test-planner`
* **Назначение**: Генерация тест-кейсов, планирование тестирования бизнес-процессов, проверка edge cases (test automation, business logic review).
* **Пример использования**:
  ```text
  Используй qa-test-planner для создания тест-плана функционала расчета коммунальных платежей (app/services/calculations.py).
  ```

### 3. `api-testing`
* **Источник**: `fugazi/test-automation-skills-agents/skills/api-testing`
* **Назначение**: Проверка работоспособности API, тестирование контрактов, edge case тестирование запросов (API testing).
* **Пример использования**:
  ```text
  Проверь эндпоинты в app/main.py с помощью api-testing на предмет обработки некорректных входных данных.
  ```

### 4. `playwright-regression-testing`
* **Источник**: `fugazi/test-automation-skills-agents/skills/playwright-regression-testing`
* **Назначение**: Регрессионное тестирование UI-сценариев, проверка пользовательских путей (UI / regression testing).
* **Пример использования**:
  ```text
  Используй playwright-regression-testing, чтобы сгенерировать скрипты для проверки формы добавления нового арендатора в v2.
  ```

### 5. `code-review`
* **Источник**: `addyosmani/agent-skills/skills/code-review-and-quality`
* **Назначение**: Code review, анализ качества архитектуры, проверка бизнес-логики (code review, business logic review).
* **Пример использования**:
  ```text
  Сделай code-review файла app/main.py, обратив особое внимание на работу с middleware маршрутизации v2.
  ```

---
**Примечание**: Все навыки были адаптированы под формат `SKILL.md` (добавлен YAML frontmatter) и установлены локально в папку `.antigravity/skills`.
