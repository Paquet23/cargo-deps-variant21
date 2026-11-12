"""Преобразуем граф зависимостей в текст PlantUML."""

def render(graph):
    """Даём узлам короткие имена и выделяем обратные рёбра цветом."""
    lines = ["@startuml", "!pragma layout smetana", "left to right direction"]
    aliases = {node: f"P{i}" for i, node in enumerate(graph.edges)}
    for node, alias in aliases.items():
        lines.append(f'rectangle "{node}" as {alias}')
    back_edges = set(graph.cycles)
    for source, children in graph.edges.items():
        for child in children:
            edge = (source, child)
            arrow = "-[#red]->" if edge in back_edges else "-->"
            lines.append(f"{aliases[source]} {arrow} {aliases[child]}")
    lines.append("@enduml")
    return "\n".join(lines)
