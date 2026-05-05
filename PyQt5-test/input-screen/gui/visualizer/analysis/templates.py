"""
Pre-defined equation templates organized by simulation configuration.

Each template maps a (simulation_type, polarization_mode, dimension) tuple
to a list of common analysis equations users can quickly apply.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class EquationTemplate:
    """A pre-defined equation for quick analysis."""

    name: str
    expression: str
    domain: str  # "time" or "frequency"
    description: str
    y_label: str
    y_unit: str


TEMPLATES: Dict[Tuple[str, str, str], List[EquationTemplate]] = {
    ("Wave Impedance", "TE", "2D"): [
        # Time domain
        EquationTemplate(
            "Electric Field Ex(t)",
            "Ex",
            "time",
            "Time-domain electric field at probe",
            "Ex",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hz(t)",
            "Hz",
            "time",
            "Time-domain magnetic field at probe",
            "Hz",
            "A/m",
        ),
        EquationTemplate(
            "Impedance Z(t)",
            "-Ex/Hz",
            "time",
            "Time-domain wave impedance (TE mode)",
            "Z(t)",
            "\u03a9",
        ),
        # Frequency domain
        EquationTemplate(
            "Impedance Z(f)",
            "-Ex/Hz",
            "frequency",
            "Frequency-domain wave impedance (TE mode)",
            "Z(f)",
            "\u03a9",
        ),
        EquationTemplate(
            "|Z(f)| Magnitude",
            "abs(-Ex/Hz)",
            "frequency",
            "Impedance magnitude spectrum",
            "|Z(f)|",
            "\u03a9",
        ),
        EquationTemplate(
            "Re{Z(f)}",
            "real(-Ex/Hz)",
            "frequency",
            "Real part of frequency-domain impedance",
            "Re{Z(f)}",
            "\u03a9",
        ),
        EquationTemplate(
            "Im{Z(f)}",
            "imag(-Ex/Hz)",
            "frequency",
            "Imaginary part of frequency-domain impedance",
            "Im{Z(f)}",
            "\u03a9",
        ),
    ],
    ("Wave Impedance", "TM", "2D"): [
        # Time domain
        EquationTemplate(
            "Electric Field Ez(t)",
            "Ez",
            "time",
            "Time-domain electric field at probe",
            "Ez",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hx(t)",
            "Hx",
            "time",
            "Time-domain magnetic field at probe",
            "Hx",
            "A/m",
        ),
        EquationTemplate(
            "Impedance Z(t)",
            "Ez/Hx",
            "time",
            "Time-domain wave impedance (TM mode)",
            "Z(t)",
            "\u03a9",
        ),
        # Frequency domain
        EquationTemplate(
            "Impedance Z(f)",
            "Ez/Hx",
            "frequency",
            "Frequency-domain wave impedance (TM mode)",
            "Z(f)",
            "\u03a9",
        ),
        EquationTemplate(
            "|Z(f)| Magnitude",
            "abs(Ez/Hx)",
            "frequency",
            "Impedance magnitude spectrum",
            "|Z(f)|",
            "\u03a9",
        ),
        EquationTemplate(
            "Re{Z(f)}",
            "real(Ez/Hx)",
            "frequency",
            "Real part of frequency-domain impedance",
            "Re{Z(f)}",
            "\u03a9",
        ),
        EquationTemplate(
            "Im{Z(f)}",
            "imag(Ez/Hx)",
            "frequency",
            "Imaginary part of frequency-domain impedance",
            "Im{Z(f)}",
            "\u03a9",
        ),
    ],
    ("Wave Impedance", "TE", "3D"): [
        EquationTemplate(
            "Electric Field Ey(t)",
            "Ey",
            "time",
            "Time-domain electric field at probe",
            "Ey",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hz(t)",
            "Hz",
            "time",
            "Time-domain magnetic field at probe",
            "Hz",
            "A/m",
        ),
        EquationTemplate(
            "Impedance Z(f)",
            "-Ey/Hz",
            "frequency",
            "3D TE wave impedance",
            "Z(f)",
            "\u03a9",
        ),
        EquationTemplate(
            "|Z(f)| Magnitude",
            "abs(-Ey/Hz)",
            "frequency",
            "Impedance magnitude spectrum (3D TE)",
            "|Z(f)|",
            "\u03a9",
        ),
    ],
    ("Wave Impedance", "TM", "3D"): [
        EquationTemplate(
            "Electric Field Ez(t)",
            "Ez",
            "time",
            "Time-domain electric field at probe",
            "Ez",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hy(t)",
            "Hy",
            "time",
            "Time-domain magnetic field at probe",
            "Hy",
            "A/m",
        ),
        EquationTemplate(
            "Impedance Z(f)",
            "Ez/Hy",
            "frequency",
            "3D TM wave impedance",
            "Z(f)",
            "\u03a9",
        ),
        EquationTemplate(
            "|Z(f)| Magnitude",
            "abs(Ez/Hy)",
            "frequency",
            "Impedance magnitude spectrum (3D TM)",
            "|Z(f)|",
            "\u03a9",
        ),
    ],
    ("S-Parameters", "TE", "2D"): [
        EquationTemplate(
            "|S11|",
            "abs(S11)",
            "frequency",
            "Input reflection magnitude",
            "|S11|",
            "",
        ),
        EquationTemplate(
            "|S21|",
            "abs(S21)",
            "frequency",
            "Forward transmission magnitude",
            "|S21|",
            "",
        ),
        EquationTemplate(
            "S11 Return Loss (dB)",
            "-20*log10(abs(S11)+1e-12)",
            "frequency",
            "Return loss from S11",
            "RL",
            "dB",
        ),
        EquationTemplate(
            "S21 Insertion Loss (dB)",
            "-20*log10(abs(S21)+1e-12)",
            "frequency",
            "Insertion loss from S21",
            "IL",
            "dB",
        ),
    ],
    ("S-Parameters", "TM", "2D"): [
        EquationTemplate(
            "|S11|",
            "abs(S11)",
            "frequency",
            "Input reflection magnitude",
            "|S11|",
            "",
        ),
        EquationTemplate(
            "|S21|",
            "abs(S21)",
            "frequency",
            "Forward transmission magnitude",
            "|S21|",
            "",
        ),
        EquationTemplate(
            "S11 Return Loss (dB)",
            "-20*log10(abs(S11)+1e-12)",
            "frequency",
            "Return loss from S11",
            "RL",
            "dB",
        ),
        EquationTemplate(
            "S21 Insertion Loss (dB)",
            "-20*log10(abs(S21)+1e-12)",
            "frequency",
            "Insertion loss from S21",
            "IL",
            "dB",
        ),
    ],
    ("S-Parameters", "TE", "3D"): [
        EquationTemplate(
            "|S11|",
            "abs(S11)",
            "frequency",
            "Input reflection magnitude",
            "|S11|",
            "",
        ),
        EquationTemplate(
            "|S21|",
            "abs(S21)",
            "frequency",
            "Forward transmission magnitude",
            "|S21|",
            "",
        ),
        EquationTemplate(
            "S11 Return Loss (dB)",
            "-20*log10(abs(S11)+1e-12)",
            "frequency",
            "Return loss from S11",
            "RL",
            "dB",
        ),
        EquationTemplate(
            "S21 Insertion Loss (dB)",
            "-20*log10(abs(S21)+1e-12)",
            "frequency",
            "Insertion loss from S21",
            "IL",
            "dB",
        ),
    ],
    ("S-Parameters", "TM", "3D"): [
        EquationTemplate(
            "|S11|",
            "abs(S11)",
            "frequency",
            "Input reflection magnitude",
            "|S11|",
            "",
        ),
        EquationTemplate(
            "|S21|",
            "abs(S21)",
            "frequency",
            "Forward transmission magnitude",
            "|S21|",
            "",
        ),
        EquationTemplate(
            "S11 Return Loss (dB)",
            "-20*log10(abs(S11)+1e-12)",
            "frequency",
            "Return loss from S11",
            "RL",
            "dB",
        ),
        EquationTemplate(
            "S21 Insertion Loss (dB)",
            "-20*log10(abs(S21)+1e-12)",
            "frequency",
            "Insertion loss from S21",
            "IL",
            "dB",
        ),
    ],
    ("Scattering Loss", "TE", "2D"): [
        EquationTemplate(
            "Electric Field Ex(t)",
            "Ex",
            "time",
            "Time-domain electric field at probe",
            "Ex",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hz(t)",
            "Hz",
            "time",
            "Time-domain magnetic field at probe",
            "Hz",
            "A/m",
        ),
        EquationTemplate(
            "Reflection Coefficient |Gamma|",
            "abs(((-Ex/Hz)-377)/((-Ex/Hz)+377))",
            "frequency",
            "Magnitude of reflection coefficient inferred from wave impedance",
            "|Gamma|",
            "",
        ),
        EquationTemplate(
            "Scattering Loss (dB)",
            "-20*log10(abs(((-Ex/Hz)-377)/((-Ex/Hz)+377))+1e-12)",
            "frequency",
            "Reflection-based scattering loss estimate",
            "Loss",
            "dB",
        ),
    ],
    ("Scattering Loss", "TM", "2D"): [
        EquationTemplate(
            "Electric Field Ez(t)",
            "Ez",
            "time",
            "Time-domain electric field at probe",
            "Ez",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hx(t)",
            "Hx",
            "time",
            "Time-domain magnetic field at probe",
            "Hx",
            "A/m",
        ),
        EquationTemplate(
            "Reflection Coefficient |Gamma|",
            "abs(((Ez/Hx)-377)/((Ez/Hx)+377))",
            "frequency",
            "Magnitude of reflection coefficient inferred from wave impedance",
            "|Gamma|",
            "",
        ),
        EquationTemplate(
            "Scattering Loss (dB)",
            "-20*log10(abs(((Ez/Hx)-377)/((Ez/Hx)+377))+1e-12)",
            "frequency",
            "Reflection-based scattering loss estimate",
            "Loss",
            "dB",
        ),
    ],
    ("Scattering Loss", "TE", "3D"): [
        EquationTemplate(
            "Electric Field Ey(t)",
            "Ey",
            "time",
            "Time-domain electric field at probe",
            "Ey",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hz(t)",
            "Hz",
            "time",
            "Time-domain magnetic field at probe",
            "Hz",
            "A/m",
        ),
        EquationTemplate(
            "Reflection Coefficient |Gamma|",
            "abs(((-Ey/Hz)-377)/((-Ey/Hz)+377))",
            "frequency",
            "Magnitude of reflection coefficient inferred from wave impedance",
            "|Gamma|",
            "",
        ),
        EquationTemplate(
            "Scattering Loss (dB)",
            "-20*log10(abs(((-Ey/Hz)-377)/((-Ey/Hz)+377))+1e-12)",
            "frequency",
            "Reflection-based scattering loss estimate",
            "Loss",
            "dB",
        ),
    ],
    ("Scattering Loss", "TM", "3D"): [
        EquationTemplate(
            "Electric Field Ez(t)",
            "Ez",
            "time",
            "Time-domain electric field at probe",
            "Ez",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hy(t)",
            "Hy",
            "time",
            "Time-domain magnetic field at probe",
            "Hy",
            "A/m",
        ),
        EquationTemplate(
            "Reflection Coefficient |Gamma|",
            "abs(((Ez/Hy)-377)/((Ez/Hy)+377))",
            "frequency",
            "Magnitude of reflection coefficient inferred from wave impedance",
            "|Gamma|",
            "",
        ),
        EquationTemplate(
            "Scattering Loss (dB)",
            "-20*log10(abs(((Ez/Hy)-377)/((Ez/Hy)+377))+1e-12)",
            "frequency",
            "Reflection-based scattering loss estimate",
            "Loss",
            "dB",
        ),
    ],
    ("Custom Experiment", "TE", "2D"): [
        EquationTemplate(
            "Electric Field Ex(t)",
            "Ex",
            "time",
            "Time-domain electric field at probe",
            "Ex",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hz(t)",
            "Hz",
            "time",
            "Time-domain magnetic field at probe",
            "Hz",
            "A/m",
        ),
        EquationTemplate(
            "Impedance Z(f)",
            "-Ex/Hz",
            "frequency",
            "Frequency-domain impedance view",
            "Z(f)",
            "\u03a9",
        ),
    ],
    ("Custom Experiment", "TM", "2D"): [
        EquationTemplate(
            "Electric Field Ez(t)",
            "Ez",
            "time",
            "Time-domain electric field at probe",
            "Ez",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hx(t)",
            "Hx",
            "time",
            "Time-domain magnetic field at probe",
            "Hx",
            "A/m",
        ),
        EquationTemplate(
            "Impedance Z(f)",
            "Ez/Hx",
            "frequency",
            "Frequency-domain impedance view",
            "Z(f)",
            "\u03a9",
        ),
    ],
    ("Custom Experiment", "TE", "3D"): [
        EquationTemplate(
            "Electric Field Ey(t)",
            "Ey",
            "time",
            "Time-domain electric field at probe",
            "Ey",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hz(t)",
            "Hz",
            "time",
            "Time-domain magnetic field at probe",
            "Hz",
            "A/m",
        ),
        EquationTemplate(
            "Impedance Z(f)",
            "-Ey/Hz",
            "frequency",
            "Frequency-domain impedance view",
            "Z(f)",
            "\u03a9",
        ),
    ],
    ("Custom Experiment", "TM", "3D"): [
        EquationTemplate(
            "Electric Field Ez(t)",
            "Ez",
            "time",
            "Time-domain electric field at probe",
            "Ez",
            "V/m",
        ),
        EquationTemplate(
            "Magnetic Field Hy(t)",
            "Hy",
            "time",
            "Time-domain magnetic field at probe",
            "Hy",
            "A/m",
        ),
        EquationTemplate(
            "Impedance Z(f)",
            "Ez/Hy",
            "frequency",
            "Frequency-domain impedance view",
            "Z(f)",
            "\u03a9",
        ),
    ],
}


def get_templates(
    simulation_type: str,
    polarization_mode: str,
    dimension: str = "2D",
) -> List[EquationTemplate]:
    """Get all templates for a given simulation configuration."""
    key = (simulation_type, polarization_mode, dimension)
    return list(TEMPLATES.get(key, []))


def get_templates_by_domain(
    simulation_type: str,
    polarization_mode: str,
    dimension: str = "2D",
    domain: Optional[str] = None,
) -> List[EquationTemplate]:
    """Get templates filtered by domain ('time' or 'frequency')."""
    templates = get_templates(simulation_type, polarization_mode, dimension)
    if domain is None:
        return templates
    return [t for t in templates if t.domain == domain]
