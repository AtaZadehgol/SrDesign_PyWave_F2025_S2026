import re

"""Parses the solver output into percentages for the progress bar and output dialog to make the information more cohesive for users."""

# ── percentage tags for individual lines ─────────────────────────────────────

STEP_PATTERNS = [
    (r'Loaded JSON',                 9),
    (r'Configuration',              11),
    (r'Importing solver',           13),
    (r'Created solver strategy',    15),
    (r'Validating Input',           16),
    (r'Input validation passed',    17),
    (r'Configuring Inital',         18),
    (r'Initial Values Configured',  20),
    (r'Solver is ready',            21),
    (r'simulation size will be',    22),
    (r'Permittivity Map',           25),
    (r'Permeability Map',           28),
    (r'Measurement Regions',        31),
    (r'Transferring.*GPU',          34),
    (r'Multi-source mode',          37),
    (r'Converting measurement',     40),
    (r'loop started',               44),
    (r'FDTD loop time was',         97),
    (r'Saving results',             97),
    (r'Saved Measurement',          98),
    (r'results saved in',           99),
    (r'Writing Metadata',           99),
]


def tag_line(line):
    """Attach a [PROGRESS: N] token to a line."""
    m = re.search(r'(\d+(?:\.\d+)?)\s*%\s*complete', line)
    if m:
        raw = float(m.group(1))
        pct = int(44 + (min(raw, 100) / 100) * 52)
        return f"[PROGRESS: {pct}] {line}"

    for pattern, pct in STEP_PATTERNS:
        if re.search(pattern, line):
            return f"[PROGRESS: {pct}] {line}"

    return line


# ── section classifiers ───────────────────────────────────────────────────────

def _is_timestep(line):
    return bool(re.search(r'%\s*complete', line))

def _is_results_line(line):
    return bool(re.search(
        r'FDTD loop time|Saving results|Saved Measurement|results saved in|Writing Metadata|Speed in MC',
        line
    ))

def _is_config_end(line):
    """Last line of the configuration phase."""
    return bool(re.search(r'Solver is ready|simulation size will be', line))

def _is_init_end(line):
    """Last line of the initialization phase."""
    return bool(re.search(r'loop started', line))


# ── phase tracker ─────────────────────────────────────────────────────────────

PHASE_CONFIG = 'config'
PHASE_INIT   = 'init'
PHASE_LOOP   = 'loop'
PHASE_DONE   = 'done'


# ── main grouping iterator ────────────────────────────────────────────────────

def iter_grouped(stream, emit_fn):
    """
    Emits solver output grouped into four named sections:

      [SECTION: Configuration]   9–22%   — JSON load, strategy, validation, initial values
      [SECTION: Initialization]  23–43%  — permittivity/permeability maps, GPU, measurement setup
      [PROGRESS: N] Step X of Y  44–96%  — one emit per FDTD timestep, details expandable
      [SECTION: Results]         97–99%  — save/metadata lines

    Directory info (5% and 8%) is emitted individually by solver_worker before
    this function is called, so it appears as its own rows in the log.
    """
    phase = PHASE_CONFIG
    config_lines = []
    init_lines = []
    results_lines = []

    pending_step = None
    pending_details = []

    for raw in stream:
        line = raw.strip()

        if not line:
            # Blank line flushes a buffered timestep block
            if pending_step:
                emit_fn(pending_step + "\n" + "\n".join(pending_details))
                pending_step = None
                pending_details = []
            continue

        # ── post-loop results lines ───────────────────────────────────────
        if phase == PHASE_DONE and _is_results_line(line):
            results_lines.append(line)
            continue

        # ── FDTD timestep header ──────────────────────────────────────────
        if _is_timestep(line):
            phase = PHASE_LOOP
            if pending_step:
                emit_fn(pending_step + "\n" + "\n".join(pending_details))
                pending_details = []
            pending_step = tag_line(line)
            continue

        # ── detail lines for current timestep ────────────────────────────
        if pending_step:
            if _is_results_line(line):
                # Loop just ended, flush timestep then switch phase
                emit_fn(pending_step + "\n" + "\n".join(pending_details))
                pending_step = None
                pending_details = []
                phase = PHASE_DONE
                results_lines.append(line)
            else:
                pending_details.append(line)
            continue

        # ── configuration phase ───────────────────────────────────────────
        if phase == PHASE_CONFIG:
            config_lines.append(line)
            if _is_config_end(line):
                phase = PHASE_INIT
                emit_fn(
                    "[PROGRESS: 22] [SECTION: Configuration]\n"
                    + "\n".join(config_lines)
                )
                config_lines = []
            continue

        # ── initialization phase ──────────────────────────────────────────
        if phase == PHASE_INIT:
            init_lines.append(line)
            if _is_init_end(line):
                phase = PHASE_LOOP
                emit_fn(
                    "[PROGRESS: 44] [SECTION: Initialization]\n"
                    + "\n".join(init_lines)
                )
                init_lines = []
            continue

        # ── catch-all for any unclassified lines after loop ───────────────
        if phase in (PHASE_LOOP, PHASE_DONE):
            results_lines.append(line)

    # ── flush anything remaining ──────────────────────────────────────────
    if pending_step:
        emit_fn(pending_step + "\n" + "\n".join(pending_details))

    if config_lines:
        emit_fn(
            "[PROGRESS: 22] [SECTION: Configuration]\n"
            + "\n".join(config_lines)
        )

    if init_lines:
        emit_fn(
            "[PROGRESS: 44] [SECTION: Initialization]\n"
            + "\n".join(init_lines)
        )

    if results_lines:
        emit_fn(
            "[PROGRESS: 99] [SECTION: Results]\n"
            + "\n".join(results_lines)
        )