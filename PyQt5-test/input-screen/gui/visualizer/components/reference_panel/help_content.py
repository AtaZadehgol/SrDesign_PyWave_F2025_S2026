"""Reference panel HTML content helpers."""


def default_reference_html() -> str:
    """Return placeholder HTML shown before results are loaded."""
    return (
        "<h3>Equation Reference</h3>"
        "<p style='color:#666;'>Load results to see available "
        "variables and functions.</p>"
    )


def build_reference_html(functions, constants, measurement_point_info) -> str:
    """Build reference panel HTML from available symbols and metadata."""
    html_parts = ["<h3>Equation Reference</h3>"]
    html_parts.append("<h4>Operators</h4>" "<p><code>+ - * / **</code></p>")

    html_parts.append("<h4>Functions</h4><ul>")
    for fn in functions:
        html_parts.append(f"<li><code>{fn}()</code></li>")
    html_parts.append("</ul>")

    html_parts.append("<h4>Constants</h4><ul>")
    for constant_name in constants:
        html_parts.append(f"<li><code>{constant_name}</code></li>")
    html_parts.append("</ul>")

    if measurement_point_info:
        html_parts.append("<h4>Measurement Points</h4>")
        html_parts.append(
            "<p><i>Indexing examples:</i></p>"
            "<ul>"
            "<li><code>Var</code>: full multi-point data</li>"
            "<li><code>Var_mean</code>: mean over spatial points</li>"
            "<li><code>Var[5]</code>: point index 5 (time series)</li>"
            "<li><code>Var[5, 100:300]</code>: point index 5 with a time slice</li>"
            "<li><code>SurfaceVar[1, 1, :]</code>: surface point (x=1, y=1) over time</li>"
            "<li><code>SurfaceVar[:, :, 200]</code>: full surface snapshot at time index 200</li>"
            "</ul>"
        )

    return "".join(html_parts)
