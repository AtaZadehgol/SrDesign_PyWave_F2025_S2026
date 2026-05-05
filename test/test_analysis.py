"""
Tests for the visualizer analysis package.

Covers:
- EquationEngine: safe evaluation, security validation, math correctness
- FieldLoader: file mapping, loading, shape validation
- ProbeExtractor: midpoint extraction, custom index
- Analyzer: end-to-end pipeline with synthetic data
"""

import json
import os
import sys
import warnings
import pytest
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for testing
import numpy as np
from pathlib import Path
from tempfile import TemporaryDirectory

# Add visualizer package to path so we can import the analysis sub-package
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "PyQt5-test",
        "input-screen",
        "gui",
        "visualizer",
    ),
)

from analysis.equation_engine import EquationEngine
from analysis.field_loader import FieldLoader, FIELD_FILES
from analysis.probe import ProbeExtractor
from analysis.templates import get_templates, get_templates_by_domain, EquationTemplate
from analysis.analyzer import Analyzer


# ---------------------------------------------------------------------------
# EquationEngine tests
# ---------------------------------------------------------------------------


class TestEquationEngine:
    """Tests for the safe expression evaluator."""

    def setup_method(self):
        self.ex = np.array([1.0, 2.0, 3.0, 4.0])
        self.hz = np.array([0.5, 1.0, 1.5, 2.0])
        self.engine = EquationEngine({"Ex": self.ex, "Hz": self.hz})

    def test_simple_variable(self):
        result = self.engine.evaluate("Ex")
        np.testing.assert_array_almost_equal(np.real(result), self.ex)

    def test_negation(self):
        result = self.engine.evaluate("-Ex")
        np.testing.assert_array_almost_equal(np.real(result), -self.ex)

    def test_division(self):
        result = self.engine.evaluate("-Ex/Hz")
        expected = -self.ex / self.hz
        np.testing.assert_array_almost_equal(np.real(result), expected)

    def test_addition(self):
        result = self.engine.evaluate("Ex + Hz")
        expected = self.ex + self.hz
        np.testing.assert_array_almost_equal(np.real(result), expected)

    def test_multiplication(self):
        result = self.engine.evaluate("Ex * Hz")
        expected = self.ex * self.hz
        np.testing.assert_array_almost_equal(np.real(result), expected)

    def test_power(self):
        result = self.engine.evaluate("Ex ** 2")
        expected = self.ex**2
        np.testing.assert_array_almost_equal(np.real(result), expected)

    def test_abs_function(self):
        result = self.engine.evaluate("abs(-Ex/Hz)")
        expected = np.abs(-self.ex / self.hz)
        np.testing.assert_array_almost_equal(np.real(result), expected)

    def test_sqrt_function(self):
        result = self.engine.evaluate("sqrt(Ex)")
        expected = np.sqrt(self.ex)
        np.testing.assert_array_almost_equal(np.real(result), expected)

    def test_constant_pi(self):
        result = self.engine.evaluate("Ex * pi")
        expected = self.ex * np.pi
        np.testing.assert_array_almost_equal(np.real(result), expected)

    def test_division_by_zero_produces_nan(self):
        engine = EquationEngine({"A": np.array([1.0, 2.0]), "B": np.array([0.0, 1.0])})
        result = engine.evaluate("A/B")
        assert np.isnan(result[0])
        np.testing.assert_almost_equal(np.real(result[1]), 2.0)

    # --- Safety/security tests ---

    def test_reject_import(self):
        valid, reason = self.engine.validate("__import__('os')")
        assert not valid
        assert "Disallowed" in reason or "Unknown" in reason

    def test_reject_attribute_access(self):
        valid, reason = self.engine.validate("Ex.__class__")
        assert not valid

    def test_reject_unknown_variable(self):
        valid, reason = self.engine.validate("unknown_var")
        assert not valid
        assert "Unknown" in reason

    def test_reject_unknown_function(self):
        valid, reason = self.engine.validate("open('file')")
        assert not valid

    def test_reject_exec(self):
        valid, reason = self.engine.validate("exec('print(1)')")
        assert not valid

    def test_reject_empty_expression(self):
        valid, reason = self.engine.validate("")
        assert not valid

    def test_reject_syntax_error(self):
        valid, reason = self.engine.validate("Ex +")
        assert not valid
        assert "Syntax" in reason

    def test_evaluate_invalid_expression_raises(self):
        with pytest.raises(ValueError):
            self.engine.evaluate("__import__('os')")

    def test_get_available_names(self):
        names = self.engine.get_available_names()
        assert "Ex" in names
        assert "Hz" in names

    def test_get_available_functions(self):
        funcs = self.engine.get_available_functions()
        assert "abs" in funcs
        assert "sqrt" in funcs
        assert "sin" in funcs


# ---------------------------------------------------------------------------
# FieldLoader tests
# ---------------------------------------------------------------------------


class TestFieldLoader:
    """Tests for simulation-aware field loading."""

    def test_load_te_2d(self):
        with TemporaryDirectory() as tmpdir:
            ex = np.random.rand(100, 50).astype(np.float32)
            hz = np.random.rand(100, 50).astype(np.float32)
            np.save(os.path.join(tmpdir, "ex_zwave.npy"), ex)
            np.save(os.path.join(tmpdir, "hz_zwave.npy"), hz)

            loader = FieldLoader(tmpdir)
            fields = loader.load("Wave Impedance", "TE", "2D")

            assert "Ex" in fields
            assert "Hz" in fields
            np.testing.assert_array_equal(fields["Ex"], ex)
            np.testing.assert_array_equal(fields["Hz"], hz)

    def test_load_tm_2d(self):
        with TemporaryDirectory() as tmpdir:
            ez = np.random.rand(100, 50).astype(np.float32)
            hx = np.random.rand(100, 50).astype(np.float32)
            np.save(os.path.join(tmpdir, "ez_zwave.npy"), ez)
            np.save(os.path.join(tmpdir, "hx_zwave.npy"), hx)

            loader = FieldLoader(tmpdir)
            fields = loader.load("Wave Impedance", "TM", "2D")

            assert "Ez" in fields
            assert "Hx" in fields

    def test_load_scattering_loss_tm_2d(self):
        with TemporaryDirectory() as tmpdir:
            ez = np.random.rand(100, 50).astype(np.float32)
            hx = np.random.rand(100, 50).astype(np.float32)
            np.save(os.path.join(tmpdir, "ez_zwave.npy"), ez)
            np.save(os.path.join(tmpdir, "hx_zwave.npy"), hx)

            loader = FieldLoader(tmpdir)
            fields = loader.load("Scattering Loss", "TM", "2D")

            assert "Ez" in fields
            assert "Hx" in fields
            np.testing.assert_array_equal(fields["Ez"], ez)
            np.testing.assert_array_equal(fields["Hx"], hx)

    def test_load_scattering_loss_normalized_config(self):
        with TemporaryDirectory() as tmpdir:
            ex = np.random.rand(100, 50).astype(np.float32)
            hz = np.random.rand(100, 50).astype(np.float32)
            np.save(os.path.join(tmpdir, "ex_zwave.npy"), ex)
            np.save(os.path.join(tmpdir, "hz_zwave.npy"), hz)

            loader = FieldLoader(tmpdir)
            fields = loader.load("scattering-loss", "te", "2d")

            assert "Ex" in fields
            assert "Hz" in fields
            np.testing.assert_array_equal(fields["Ex"], ex)
            np.testing.assert_array_equal(fields["Hz"], hz)

    def test_load_scattering_loss_fft_files(self):
        with TemporaryDirectory() as tmpdir:
            ex = (
                np.random.rand(64) + 1j * np.random.rand(64)
            ).astype(np.complex64)
            hz = (
                np.random.rand(64) + 1j * np.random.rand(64)
            ).astype(np.complex64)
            np.save(os.path.join(tmpdir, "ex_fft.npy"), ex)
            np.save(os.path.join(tmpdir, "hz_fft.npy"), hz)

            loader = FieldLoader(tmpdir)
            fields = loader.load("Scattering Loss", "TE", "2D")

            assert "Ex" in fields
            assert "Hz" in fields
            assert "Ex" in loader.frequency_domain_variables
            assert "Hz" in loader.frequency_domain_variables
            np.testing.assert_array_equal(fields["Ex"], ex)
            np.testing.assert_array_equal(fields["Hz"], hz)

    def test_load_prefers_fft_when_both_variants_exist(self):
        with TemporaryDirectory() as tmpdir:
            ex_time = np.random.rand(64, 8).astype(np.float32)
            hz_time = np.random.rand(64, 8).astype(np.float32)
            ex_fft = (
                np.random.rand(64) + 1j * np.random.rand(64)
            ).astype(np.complex64)
            hz_fft = (
                np.random.rand(64) + 1j * np.random.rand(64)
            ).astype(np.complex64)

            np.save(os.path.join(tmpdir, "ex_zwave.npy"), ex_time)
            np.save(os.path.join(tmpdir, "hz_zwave.npy"), hz_time)
            np.save(os.path.join(tmpdir, "ex_fft.npy"), ex_fft)
            np.save(os.path.join(tmpdir, "hz_fft.npy"), hz_fft)

            loader = FieldLoader(tmpdir)
            fields = loader.load("Scattering Loss", "TE", "2D")

            assert "Ex" in loader.frequency_domain_variables
            assert "Hz" in loader.frequency_domain_variables
            np.testing.assert_array_equal(fields["Ex"], ex_fft)
            np.testing.assert_array_equal(fields["Hz"], hz_fft)

    def test_discover_measurement_points_fft_files(self):
        with TemporaryDirectory() as tmpdir:
            metadata = {
                "name": "Measurement Surface 1",
                "type": "surface",
                "num_points": 4,
                "shape": [2, 2],
            }
            with open(os.path.join(tmpdir, "metadata_Measurement_Surface_1.json"), "w") as f:
                json.dump(metadata, f)

            ex_surface = (
                np.random.rand(4) + 1j * np.random.rand(4)
            ).astype(np.complex64)
            np.save(
                os.path.join(tmpdir, "ex_Measurement_Surface_1_fft.npy"),
                ex_surface,
            )

            loader = FieldLoader(tmpdir)
            points = loader.discover_measurement_points()

            assert len(points) == 1
            assert points[0].safe_name == "Measurement_Surface_1"
            assert "Ex" in points[0].available_fields

    def test_load_measurement_point_fft_files(self):
        with TemporaryDirectory() as tmpdir:
            surface = (
                np.random.rand(6) + 1j * np.random.rand(6)
            ).astype(np.complex64)
            np.save(
                os.path.join(tmpdir, "ex_Measurement_Surface_1_fft.npy"),
                surface,
            )

            loader = FieldLoader(tmpdir)
            mp_data = loader.load_measurement_point("Measurement_Surface_1")

            assert "Ex" in mp_data
            assert "Ex_Measurement_Surface_1" in loader.frequency_domain_variables
            np.testing.assert_array_equal(mp_data["Ex"], surface)

    def test_load_measurement_point_prefers_fft_when_both_variants_exist(self):
        with TemporaryDirectory() as tmpdir:
            surface_time = np.random.rand(10, 4).astype(np.float32)
            surface_fft = (
                np.random.rand(4) + 1j * np.random.rand(4)
            ).astype(np.complex64)

            np.save(
                os.path.join(tmpdir, "ex_Measurement_Surface_1.npy"),
                surface_time,
            )
            np.save(
                os.path.join(tmpdir, "ex_Measurement_Surface_1_fft.npy"),
                surface_fft,
            )

            loader = FieldLoader(tmpdir)
            mp_data = loader.load_measurement_point("Measurement_Surface_1")

            assert "Ex_Measurement_Surface_1" in loader.frequency_domain_variables
            np.testing.assert_array_equal(mp_data["Ex"], surface_fft)

    def test_load_missing_file_raises(self):
        with TemporaryDirectory() as tmpdir:
            np.save(os.path.join(tmpdir, "ex_zwave.npy"), np.zeros((10, 5)))
            # Missing hz_zwave.npy

            loader = FieldLoader(tmpdir)
            with pytest.raises(FileNotFoundError):
                loader.load("Wave Impedance", "TE", "2D")

    def test_load_shape_mismatch_raises(self):
        with TemporaryDirectory() as tmpdir:
            np.save(os.path.join(tmpdir, "ex_zwave.npy"), np.zeros((100, 50)))
            np.save(os.path.join(tmpdir, "hz_zwave.npy"), np.zeros((100, 40)))

            loader = FieldLoader(tmpdir)
            with pytest.raises(ValueError, match="Shape mismatch"):
                loader.load("Wave Impedance", "TE", "2D")

    def test_unknown_config_raises(self):
        with TemporaryDirectory() as tmpdir:
            loader = FieldLoader(tmpdir)
            with pytest.raises(ValueError, match="Unknown simulation"):
                loader.load("Unknown Type", "XX", "9D")

    def test_get_available_variables(self):
        vars_te = FieldLoader.get_available_variables("Wave Impedance", "TE", "2D")
        assert "Ex" in vars_te
        assert "Hz" in vars_te

        vars_tm = FieldLoader.get_available_variables("Wave Impedance", "TM", "2D")
        assert "Ez" in vars_tm
        assert "Hx" in vars_tm

    def test_get_available_variables_unknown(self):
        result = FieldLoader.get_available_variables("Unknown", "XX", "9D")
        assert result == []


# ---------------------------------------------------------------------------
# ProbeExtractor tests
# ---------------------------------------------------------------------------


class TestProbeExtractor:
    """Tests for probe point extraction."""

    def test_default_midpoint(self):
        fields = {
            "Ex": np.arange(200).reshape(20, 10).astype(float),
            "Hz": np.arange(200).reshape(20, 10).astype(float) * 0.5,
        }
        extractor = ProbeExtractor(fields)
        assert extractor.probe_index == 5  # 10 // 2

        probe = extractor.extract()
        assert "Ex" in probe
        assert "Hz" in probe
        assert probe["Ex"].shape == (20,)
        # Column 5 of the original
        np.testing.assert_array_equal(probe["Ex"], fields["Ex"][:, 5])

    def test_custom_index(self):
        fields = {"A": np.ones((50, 30))}
        extractor = ProbeExtractor(fields, probe_index=7)
        assert extractor.probe_index == 7

    def test_out_of_range_raises(self):
        fields = {"A": np.ones((50, 30))}
        with pytest.raises(IndexError):
            ProbeExtractor(fields, probe_index=30)

    def test_negative_index_raises(self):
        fields = {"A": np.ones((50, 30))}
        with pytest.raises(IndexError):
            ProbeExtractor(fields, probe_index=-1)

    def test_1d_series_passthrough(self):
        fields = {
            "S11": np.linspace(0.1, 0.9, 32),
            "S21": np.linspace(0.8, 0.2, 32),
        }
        extractor = ProbeExtractor(fields)
        probe = extractor.extract()

        assert probe["S11"].shape == (32,)
        np.testing.assert_array_equal(probe["S11"], fields["S11"])
        np.testing.assert_array_equal(probe["S21"], fields["S21"])


# ---------------------------------------------------------------------------
# Templates tests
# ---------------------------------------------------------------------------


class TestTemplates:
    """Tests for template equation definitions."""

    def test_te_2d_templates_exist(self):
        templates = get_templates("Wave Impedance", "TE", "2D")
        assert len(templates) > 0

    def test_tm_2d_templates_exist(self):
        templates = get_templates("Wave Impedance", "TM", "2D")
        assert len(templates) > 0

    def test_s_parameters_templates_exist(self):
        templates = get_templates("S-Parameters", "TE", "2D")
        assert len(templates) > 0

    def test_scattering_loss_templates_exist(self):
        templates = get_templates("Scattering Loss", "TE", "2D")
        assert len(templates) > 0
        assert any(t.expression == "Ex" for t in templates)
        assert any(t.expression == "Hz" for t in templates)
        assert any(t.name == "Scattering Loss (dB)" for t in templates)

    def test_custom_experiment_templates_exist(self):
        templates = get_templates("Custom Experiment", "TE", "2D")
        assert len(templates) > 0

    def test_filter_by_time_domain(self):
        time_templates = get_templates_by_domain("Wave Impedance", "TE", "2D", "time")
        assert all(t.domain == "time" for t in time_templates)
        assert len(time_templates) > 0

    def test_filter_by_frequency_domain(self):
        freq_templates = get_templates_by_domain(
            "Wave Impedance", "TE", "2D", "frequency"
        )
        assert all(t.domain == "frequency" for t in freq_templates)
        assert len(freq_templates) > 0

    def test_unknown_config_returns_empty(self):
        templates = get_templates("Unknown", "XX", "9D")
        assert templates == []

    def test_templates_have_required_fields(self):
        templates = get_templates("Wave Impedance", "TE", "2D")
        for t in templates:
            assert t.name
            assert t.expression
            assert t.domain in ("time", "frequency")
            assert t.y_label
            assert t.y_unit


# ---------------------------------------------------------------------------
# Analyzer end-to-end tests
# ---------------------------------------------------------------------------


class TestAnalyzer:
    """Integration tests for the full analysis pipeline."""

    def _create_synthetic_project(
        self, tmpdir, sim_type="Wave Impedance", pol_mode="TE", dimension="2D"
    ):
        """Create a synthetic project directory with field data and metadata."""
        results_dir = os.path.join(tmpdir, "Results")
        os.makedirs(results_dir, exist_ok=True)

        nt, ny = 200, 60
        dt = 1e-17

        if sim_type == "Wave Impedance" and pol_mode == "TE" and dimension == "2D":
            ex = np.sin(np.linspace(0, 4 * np.pi, nt))[:, None] * np.ones(ny)
            hz = 0.5 * np.sin(np.linspace(0, 4 * np.pi, nt))[:, None] * np.ones(ny)
            np.save(os.path.join(results_dir, "ex_zwave.npy"), ex.astype(np.float32))
            np.save(os.path.join(results_dir, "hz_zwave.npy"), hz.astype(np.float32))
        elif sim_type == "Wave Impedance" and pol_mode == "TM" and dimension == "2D":
            ez = np.sin(np.linspace(0, 4 * np.pi, nt))[:, None] * np.ones(ny)
            hx = 0.5 * np.sin(np.linspace(0, 4 * np.pi, nt))[:, None] * np.ones(ny)
            np.save(os.path.join(results_dir, "ez_zwave.npy"), ez.astype(np.float32))
            np.save(os.path.join(results_dir, "hx_zwave.npy"), hx.astype(np.float32))
        elif sim_type == "S-Parameters":
            axis = np.linspace(0.0, 1.0, nt)
            np.save(os.path.join(results_dir, "s11.npy"), (0.4 * np.exp(-axis)).astype(np.float32))
            np.save(os.path.join(results_dir, "s21.npy"), (0.6 * np.exp(-0.5 * axis)).astype(np.float32))
            np.save(os.path.join(results_dir, "s12.npy"), (0.15 * np.ones(nt)).astype(np.float32))
            np.save(os.path.join(results_dir, "s22.npy"), (0.35 * np.exp(-0.8 * axis)).astype(np.float32))
        elif sim_type in ("Scattering Loss", "Custom Experiment"):
            if pol_mode == "TM":
                ez = np.sin(np.linspace(0, 4 * np.pi, nt))[:, None] * np.ones(ny)
                hx = 0.5 * np.sin(np.linspace(0, 4 * np.pi, nt))[:, None] * np.ones(ny)
                np.save(os.path.join(results_dir, "ez_zwave.npy"), ez.astype(np.float32))
                np.save(os.path.join(results_dir, "hx_zwave.npy"), hx.astype(np.float32))
            else:
                ex = np.sin(np.linspace(0, 4 * np.pi, nt))[:, None] * np.ones(ny)
                hz = 0.5 * np.sin(np.linspace(0, 4 * np.pi, nt))[:, None] * np.ones(ny)
                np.save(os.path.join(results_dir, "ex_zwave.npy"), ex.astype(np.float32))
                np.save(os.path.join(results_dir, "hz_zwave.npy"), hz.astype(np.float32))

        metadata = {
            "project_name": "test_project",
            "simulation_type": sim_type,
            "polarization_mode": pol_mode,
            "dimension": dimension,
            "results_path": "./Results",
            "solver_parameters": {"dt": dt, "nt": nt, "ny": ny},
        }
        with open(os.path.join(tmpdir, "project_metadata.json"), "w") as f:
            json.dump(metadata, f)

        return results_dir, metadata

    def test_load_te_2d(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(tmpdir)
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", cfg)
            analyzer.load()

            assert analyzer.probe_data is not None
            assert "Ex" in analyzer.probe_data
            assert "Hz" in analyzer.probe_data

    def test_load_s_parameters(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(
                tmpdir,
                sim_type="S-Parameters",
                pol_mode="TE",
                dimension="2D",
            )
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "S-Parameters", "TE", "2D", cfg)
            analyzer.load()

            assert "S11" in analyzer.probe_data
            assert "S21" in analyzer.probe_data
            assert analyzer.probe_data["S11"].ndim == 1

    def test_load_scattering_loss(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(
                tmpdir,
                sim_type="Scattering Loss",
                pol_mode="TE",
                dimension="2D",
            )
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Scattering Loss", "TE", "2D", cfg)
            analyzer.load()

            assert "Ex" in analyzer.probe_data
            assert "Hz" in analyzer.probe_data

    def test_load_scattering_loss_tm(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(
                tmpdir,
                sim_type="Scattering Loss",
                pol_mode="TM",
                dimension="2D",
            )
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Scattering Loss", "TM", "2D", cfg)
            analyzer.load()

            assert "Ez" in analyzer.probe_data
            assert "Hx" in analyzer.probe_data

    def test_load_scattering_loss_fft_synthesizes_time_series(self):
        with TemporaryDirectory() as tmpdir:
            results_dir = os.path.join(tmpdir, "Results")
            os.makedirs(results_dir, exist_ok=True)

            ex_freq = (np.random.rand(33) + 1j * np.random.rand(33)).astype(np.complex64)
            hz_freq = (np.random.rand(33) + 1j * np.random.rand(33)).astype(np.complex64)
            np.save(os.path.join(results_dir, "ex_fft.npy"), ex_freq)
            np.save(os.path.join(results_dir, "hz_fft.npy"), hz_freq)

            cfg = {"dt": 2e-15}
            analyzer = Analyzer(results_dir, "Scattering Loss", "TE", "2D", cfg)
            analyzer.load()

            assert analyzer.freq_data is not None
            assert analyzer.probe_data is not None
            assert analyzer.time_axis is not None
            assert analyzer.freq_axis is not None

            np.testing.assert_array_equal(analyzer.freq_data["Ex"], ex_freq)
            np.testing.assert_array_equal(analyzer.freq_data["Hz"], hz_freq)

            expected_nt = (len(ex_freq) - 1) * 2
            assert analyzer.probe_data["Ex"].shape == (expected_nt,)
            assert analyzer.probe_data["Hz"].shape == (expected_nt,)
            assert analyzer.time_axis.shape[0] == expected_nt
            assert analyzer.freq_axis.shape[0] == len(ex_freq)

    def test_load_custom_experiment(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(
                tmpdir,
                sim_type="Custom Experiment",
                pol_mode="TE",
                dimension="2D",
            )
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Custom Experiment", "TE", "2D", cfg)
            analyzer.load()

            assert "Ex" in analyzer.probe_data
            assert "Hz" in analyzer.probe_data
            assert analyzer.freq_data is not None
            assert analyzer.probe_data["Ex"].shape == (200,)

    def test_load_tm_2d(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(
                tmpdir, pol_mode="TM"
            )
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Wave Impedance", "TM", "2D", cfg)
            analyzer.load()

            assert "Ez" in analyzer.probe_data
            assert "Hx" in analyzer.probe_data

    def test_plot_equation_time_domain(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(tmpdir)
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", cfg)
            analyzer.load()

            fig = analyzer.plot_equation("-Ex/Hz", domain="time", title="Z(t)")
            assert fig is not None
            # Figure should have at least one axes
            assert len(fig.get_axes()) >= 1
            import matplotlib.pyplot as plt

            plt.close(fig)

    def test_plot_equation_frequency_domain(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(tmpdir)
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", cfg)
            analyzer.load()

            fig = analyzer.plot_equation("-Ex/Hz", domain="frequency", title="Z(f)")
            assert fig is not None
            assert len(fig.get_axes()) >= 1
            import matplotlib.pyplot as plt

            plt.close(fig)

    def test_create_default_plots(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(tmpdir)
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", cfg)
            analyzer.load()

            plots = analyzer.create_default_plots()
            assert len(plots) > 0
            for title, fig in plots:
                assert isinstance(title, str)
                assert fig is not None
                import matplotlib.pyplot as plt

                plt.close(fig)

    def test_load_surface_measurement_promotes_nan_dtype(self):
        with TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "Results"
            results_dir.mkdir(parents=True, exist_ok=True)

            nt = 4
            ex = np.linspace(1.0, 2.0, nt)[:, None] * np.ones((1, 8))
            hz = 0.5 * ex
            np.save(results_dir / "ex_zwave.npy", ex.astype(np.float32))
            np.save(results_dir / "hz_zwave.npy", hz.astype(np.float32))

            surface_data = np.arange(nt * 4, dtype=np.int32).reshape(nt, 4)
            np.save(results_dir / "ex_Measurement_Surface_1.npy", surface_data)

            metadata = {
                "name": "Measurement Surface 1",
                "type": "surface",
                "num_points": 4,
                "shape": [2, 2],
                "grid_indices": {
                    "x": [0, 0, 1, 1],
                    "y": [0, 0, 0, 1],
                },
            }
            with open(results_dir / "metadata_Measurement_Surface_1.json", "w") as f:
                json.dump(metadata, f)

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", {"dt": 1e-17})
            analyzer.load()

            surface_key = "Ex_Measurement_Surface_1"
            assert surface_key in analyzer.probe_data
            surface = analyzer.probe_data[surface_key]

            assert surface.dtype.kind in ("f", "c")
            assert surface.shape == (2, 2, nt)
            assert np.isnan(surface[0, 1, 0])
            np.testing.assert_array_equal(surface[1, 0, :], surface_data[:, 2])

    def test_load_measurement_mean_ignores_non_finite_without_reduce_warning(self):
        with TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "Results"
            results_dir.mkdir(parents=True, exist_ok=True)

            nt = 4
            ex = np.ones((nt, 8), dtype=np.float32)
            hz = 0.5 * ex
            np.save(results_dir / "ex_zwave.npy", ex)
            np.save(results_dir / "hz_zwave.npy", hz)

            surface_data = np.array(
                [
                    [1.0, np.inf, -np.inf, np.nan],
                    [2.0, np.inf, -np.inf, np.nan],
                    [3.0, np.inf, -np.inf, np.nan],
                    [4.0, np.inf, -np.inf, np.nan],
                ],
                dtype=np.float32,
            )
            np.save(results_dir / "ex_Measurement_Surface_1.npy", surface_data)

            metadata = {
                "name": "Measurement Surface 1",
                "type": "surface",
                "num_points": 4,
                "shape": [2, 2],
            }
            with open(results_dir / "metadata_Measurement_Surface_1.json", "w") as f:
                json.dump(metadata, f)

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", {"dt": 1e-17})

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", RuntimeWarning)
                analyzer.load()

            reduce_warnings = [
                w
                for w in caught
                if "invalid value encountered in reduce" in str(w.message)
            ]
            assert not reduce_warnings

            multiply_warnings = [
                w
                for w in caught
                if "invalid value encountered in multiply" in str(w.message)
            ]
            assert not multiply_warnings

            mean_key = "Ex_Measurement_Surface_1_mean"
            assert mean_key in analyzer.probe_data
            np.testing.assert_array_equal(analyzer.probe_data[mean_key], np.array([1.0, 2.0, 3.0, 4.0]))

    def test_aliases_measurement_fields_across_multiple_surfaces(self):
        with TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "Results"
            results_dir.mkdir(parents=True, exist_ok=True)

            nt = 5
            ex = np.ones((nt, 8), dtype=np.float32)
            hz = 0.5 * ex
            np.save(results_dir / "ex_zwave.npy", ex)
            np.save(results_dir / "hz_zwave.npy", hz)

            ex_surface = np.arange(nt * 4, dtype=np.float32).reshape(nt, 4)
            hz_surface = (100 + np.arange(nt * 4, dtype=np.float32)).reshape(nt, 4)
            np.save(results_dir / "ex_Measurement_Surface_1.npy", ex_surface)
            np.save(results_dir / "hz_Measurement_Surface_2.npy", hz_surface)

            with open(results_dir / "metadata_Measurement_Surface_1.json", "w") as f:
                json.dump(
                    {
                        "name": "Measurement Surface 1",
                        "type": "surface",
                        "num_points": 4,
                        "shape": [2, 2],
                    },
                    f,
                )

            with open(results_dir / "metadata_Measurement_Surface_2.json", "w") as f:
                json.dump(
                    {
                        "name": "Measurement Surface 2",
                        "type": "surface",
                        "num_points": 4,
                        "shape": [2, 2],
                    },
                    f,
                )

            analyzer = Analyzer(
                results_dir,
                "Wave Impedance",
                "TE",
                "2D",
                {"dt": 1e-17},
                selected_variables=[
                    "Ex",
                    "Ex_Measurement_Surface_1",
                    "Ex_Measurement_Surface_1_mean",
                    "Hz_Measurement_Surface_2",
                    "Hz_Measurement_Surface_2_mean",
                ],
            )
            analyzer.load()

            assert "Ex" in analyzer.probe_data
            assert "Hz" in analyzer.probe_data
            np.testing.assert_array_equal(
                analyzer.probe_data["Hz"],
                analyzer.probe_data["Hz_Measurement_Surface_2_mean"],
            )

    def test_keeps_base_field_when_base_and_measurement_selected(self):
        with TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "Results"
            results_dir.mkdir(parents=True, exist_ok=True)

            nt = 16
            ex = np.ones((nt, 8), dtype=np.float32)
            hz = np.linspace(0.0, 1.0, nt, dtype=np.float32)[:, None] * np.ones((1, 8), dtype=np.float32)
            np.save(results_dir / "ex_zwave.npy", ex)
            np.save(results_dir / "hz_zwave.npy", hz)

            hz_surface = np.arange(12, dtype=np.float32)
            np.save(results_dir / "hz_M_1_fft.npy", hz_surface)
            with open(results_dir / "metadata_M_1.json", "w") as f:
                json.dump(
                    {
                        "name": "M 1",
                        "type": "surface",
                        "num_points": 12,
                        "shape": [3, 4],
                    },
                    f,
                )

            analyzer = Analyzer(
                results_dir,
                "Scattering Loss",
                "TE",
                "2D",
                {"dt": 1e-17},
                selected_variables=["Ex", "Hz", "Hz_M_1", "Hz_M_1_mean"],
            )
            analyzer.load()

            # Base Hz should remain the probe time series length nt, not collapsed
            # to a one-sample measurement aggregate.
            assert analyzer.probe_data["Hz"].shape == (nt,)

    def test_surface_shape_metadata_mismatch_falls_back_to_valid_3d_surface(self):
        with TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "Results"
            results_dir.mkdir(parents=True, exist_ok=True)

            nt = 5
            ex = np.ones((nt, 8), dtype=np.float32)
            hz = 0.5 * ex
            np.save(results_dir / "ex_zwave.npy", ex)
            np.save(results_dir / "hz_zwave.npy", hz)

            # Metadata says 2x2 but data carries 6 spatial points per frame.
            # The analyzer should infer a consistent 3D surface shape.
            ex_surface = np.arange(nt * 6, dtype=np.float32).reshape(nt, 6)
            np.save(results_dir / "ex_Measurement_Surface_1.npy", ex_surface)

            with open(results_dir / "metadata_Measurement_Surface_1.json", "w") as f:
                json.dump(
                    {
                        "name": "Measurement Surface 1",
                        "type": "surface",
                        "num_points": 6,
                        "shape": [2, 2],
                    },
                    f,
                )

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", {"dt": 1e-17})
            analyzer.load()

            surface = analyzer.probe_data["Ex_Measurement_Surface_1"]
            assert surface.ndim == 3
            assert surface.shape[2] == nt
            assert surface.shape[0] * surface.shape[1] == 6
            assert "Ex_Measurement_Surface_1_mean" in analyzer.probe_data
            assert analyzer.probe_data["Ex_Measurement_Surface_1_mean"].shape == (nt,)

    def test_get_available_variables(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(tmpdir)
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", cfg)
            analyzer.load()

            variables = analyzer.get_available_variables()
            assert "Ex" in variables
            assert "Hz" in variables

    def test_get_templates(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(tmpdir)
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", cfg)
            templates = analyzer.get_templates()
            assert len(templates) > 0

            time_templates = analyzer.get_templates(domain="time")
            assert all(t.domain == "time" for t in time_templates)

    def test_plot_before_load_raises(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, _ = self._create_synthetic_project(tmpdir)
            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D")
            with pytest.raises(RuntimeError, match="Call load"):
                analyzer.plot_equation("Ex", domain="time")

    def test_probe_midpoint(self):
        """Verify the probe extracts from the spatial midpoint."""
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(tmpdir)
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D", cfg)
            analyzer.load()

            # ny=60, so midpoint is 30
            ex_full = np.load(os.path.join(results_dir, "ex_zwave.npy"))
            expected = ex_full[:, 30]
            np.testing.assert_array_almost_equal(analyzer.probe_data["Ex"], expected)

    def test_custom_probe_index(self):
        with TemporaryDirectory() as tmpdir:
            results_dir, metadata = self._create_synthetic_project(tmpdir)
            cfg = metadata["solver_parameters"]

            analyzer = Analyzer(
                results_dir, "Wave Impedance", "TE", "2D", cfg, probe_index=10
            )
            analyzer.load()

            ex_full = np.load(os.path.join(results_dir, "ex_zwave.npy"))
            expected = ex_full[:, 10]
            np.testing.assert_array_almost_equal(analyzer.probe_data["Ex"], expected)
