# Практическая №2. Вариант 21

Пекедов Дмитрий, ИКБО-17-25. CLI для анализа зависимостей пакетов Rust
из Cargo sparse-индекса. Все пять этапов представлены отдельными коммитами.

## Запуск

Требуется Python 3.10+ и PyYAML. PyYAML читает только файлы конфигурации
и тестовые графы. Программа читает сведения о пакетах сама, через HTTP
и стандартный модуль json. Cargo нужен отдельно для сравнения.

```bash
python -m pip install -r requirements.txt
python src/main.py examples/cargo.yaml
python -m unittest discover -s tests -v
```

В Windows также можно вызвать `run.bat examples/cargo.yaml`.
Запускать команды из корня проекта. Для crates.io нужен интернет.

## Настройки YAML

```yaml
package: quote
repository: https://index.crates.io
test_mode: false
exclude: ""
```

| Поле | Значение |
| --- | --- |
| package | Имя crate либо имя тестового узла из прописных латинских букв |
| repository | HTTP(S)-адрес sparse-индекса либо путь к тестовому YAML |
| test_mode | Булево значение true или false |
| exclude | Подстрока с учётом регистра или пустая строка |

Относительный путь к тестовому графу вычисляется от каталога конфигурации.
Пакет с совпадающим именем пропускается вместе с исходящими рёбрами.
Его потомки могут попасть в результат через другие ветви.

## Режимы

| Этап | Режим | Результат |
| --- | --- | --- |
| 1 | config | Параметры как ключ=значение |
| 2 | direct | Прямые зависимости с версиями |
| 3 | graph | Списки смежности и сообщения о циклах |
| 4 | order | Зависимости перед использующими их пакетами |
| 5 | plantuml | Текст диаграммы в stdout, режим по умолчанию |

```bash
python src/main.py examples/cargo.yaml --mode config
python src/main.py examples/cargo.yaml --mode direct
python src/main.py examples/diamond.yaml --mode graph
python src/main.py examples/filtered.yaml --mode graph
python src/main.py examples/leaf.yaml --mode graph
python src/main.py examples/cycle.yaml --mode graph
python src/main.py examples/self-loop.yaml --mode graph
python src/main.py examples/diamond.yaml --mode order
python src/main.py examples/cycle.yaml --mode order
```

Для ромба порядок будет D, B, E, C, A. Для цикла режим order выдаёт ошибку
с кодом 1. Граф с циклом можно посмотреть и визуализировать. Обратное
ребро будет красным. Тесты проверяют ошибки каждого поля конфигурации,
версионные ограничения, циклы, фильтр и запуск CLI.

## Визуализация и сравнение

Три примера с реальными пакетами. Команды ниже предназначены для Git Bash
или cmd. Для преобразования в SVG укажи путь к PlantUML JAR.

```bash
python src/main.py examples/cargo.yaml > quote.puml
python src/main.py examples/proc-macro2.yaml > proc-macro2.puml
python src/main.py examples/syn.yaml > syn.puml
java -jar plantuml.jar -tsvg quote.puml proc-macro2.puml syn.puml
```

См. [результаты сравнения с Cargo](COMPARISON.md).

## Как устроена программа

- `config.py` читает YAML и проверяет четыре поля. В тестовом режиме
  разрешает относительный путь от каталога файла настроек.
- `cargo_index.py` вычисляет путь к записи crate, читает версии из JSON
  по одной на строку и кэширует скачанные записи. Выбирает наибольший
  стабильный, не отозванный релиз, подходящий под требование ребра.
- `graph.py` читает тестовый список смежности и обходит граф рекурсивным
  DFS. Записанные вершины помогают не обходить узлы повторно, а множество
  активных вершин определяет обратные рёбра. Обход после потомков даёт
  порядок загрузки для графа без циклов.
- `plantuml.py` назначает вершинам идентификаторы P0, P1 и т. д.
  Затем выводит их подписи и стрелки. Каждая стрелка идёт от пакета
  к его зависимости.
- `main.py` разбирает CLI, выбирает режим и обрабатывает ошибки.

Анализатор строит граф обязательных зависимостей normal и build.
Он пропускает dev и optional, учитывает обязательные зависимости всех
платформ и работает со стабильными версиями в одном реестре. Поддерживает
обычные ограничения Cargo для стабильных версий, включая caret, tilde,
wildcard, сравнения и пересечение через запятую. Полное разрешение Cargo
включает lock-файл, features, выбор платформы, объединение версий и
возврат к другим версиям при конфликте. Результаты CLI могут отличаться.
