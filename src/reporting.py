from decimal import Decimal


def format_cell(value):
    if value is None:
        return "—"
    if isinstance(value, float):
        return format(value, ".5g")
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    return str(value).replace("|", r"\|").replace("\n", " ")


def markdown_table(headers, rows):
    def line(values):
        return "| " + " | ".join(map(format_cell, values)) + " |"

    return "\n".join([line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)])


def query_table(con, sql):
    result = con.execute(sql)
    return markdown_table([column[0] for column in result.description], result.fetchall())


def write_report(path, sections):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {path.name}")
