# Сравнение с Cargo

Сравнение выполнено на Cargo 1.99.1 и индексе crates.io 12 ноября 2026 г.
Версии фиксировались в трёх временных проектах. Для обхода ошибки TLS
Cargo использовал локальное HTTP-зеркало тех же данных crates.io.

Для повторения создай временный проект командой `cargo new --lib compare`.
В секцию `[dependencies]` его Cargo.toml добавь одну строку из таблицы.
Из каталога временного проекта выполни:

```bash
cargo tree --edges normal,build --prefix depth --no-dedupe
```

| Строка Cargo.toml | Конфигурация анализатора | Результат |
| --- | --- | --- |
| `proc-macro2 = "=1.0.107"` | examples/proc-macro2.yaml | Совпали вершины, версии и рёбра |
| `quote = "=1.0.47"` | examples/cargo.yaml | Совпали вершины, версии и рёбра |
| `syn = "=3.0.10"` | examples/syn.yaml | Cargo добавил прямое ребро syn → quote |

Ниже дерево Cargo для syn без строки временного проекта. При повторном
появлении узла в дереве повторяется его ветвь. PlantUML рисует одну
вершину на пару имени и версии.

```text
syn v3.0.10
├── proc-macro2 v1.0.107
│   └── unicode-ident v1.0.27
├── quote v1.0.47
│   └── proc-macro2 v1.0.107
│       └── unicode-ident v1.0.27
└── unicode-ident v1.0.27
```

У syn зависимость quote помечена как optional и включается через feature
printing, активную по умолчанию. Анализатор отбрасывает optional,
поэтому в его графе остаются syn → proc-macro2, syn → unicode-ident
и proc-macro2 → unicode-ident.

| Пакет | Порядок CLI | Порядок после обхода дерева Cargo от листьев |
| --- | --- | --- |
| proc-macro2 | unicode-ident, proc-macro2 | Тот же |
| quote | unicode-ident, proc-macro2, quote | Тот же |
| syn | unicode-ident, proc-macro2, syn | unicode-ident, proc-macro2, quote, syn |

Для проверки порядка сравнивали зависимости, полученные из дерева Cargo:
для каждого ребра его цель должна встретиться раньше источника. У syn
последовательность CLI сохраняет порядок общих узлов и пропускает quote.
Это сравнение топологических порядков по двум графам. Сам Cargo tree
печатает дерево от корня, а Cargo может собирать независимые узлы параллельно.

При повторении анализатор может выбрать более новые версии из индекса.
Сопоставляй вывод Cargo с версиями, которые показал анализатор.

Документация: [формат индекса](https://doc.rust-lang.org/cargo/reference/registry-index.html),
[cargo tree](https://doc.rust-lang.org/cargo/commands/cargo-tree.html),
[разрешение зависимостей](https://doc.rust-lang.org/cargo/reference/resolver.html).
