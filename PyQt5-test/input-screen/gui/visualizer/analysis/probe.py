"""
Extracts 1D probe data from full simulation field arrays.

For field arrays of shape [nt, ny], extracts a 1D time series
at a specific spatial index (default: midpoint ny // 2).
"""

import numpy as np
from typing import Dict, Optional


class ProbeExtractor:
    """
    Extracts 1D time series at a specific probe location
    from 2D field arrays of shape [nt, ny].
    """

    def __init__(
        self,
        fields: Dict[str, np.ndarray],
        probe_index: Optional[int] = None,
    ):
        """
        Args:
            fields: Dict of full field arrays, shape [nt, ny] or [nt, nx].
            probe_index: Spatial index for probe. Defaults to ny // 2.
        """
        self.fields = fields
        first_arr = next(iter(fields.values()))
        if first_arr.ndim == 1:
            self.nt = first_arr.shape[0]
            self.n_spatial = 1
            self._is_vector_data = True
        else:
            self.nt, self.n_spatial = first_arr.shape
            self._is_vector_data = False

        if probe_index is None:
            self.probe_index = self.n_spatial // 2
        else:
            self.probe_index = probe_index

        if not 0 <= self.probe_index < self.n_spatial:
            raise IndexError(
                f"Probe index {self.probe_index} out of range " f"[0, {self.n_spatial})"
            )

    def extract(self) -> Dict[str, np.ndarray]:
        """
        Extract 1D time series at probe location for all fields.

        Returns:
            Dict mapping field names to 1D arrays of shape [nt].
        """
        if self._is_vector_data:
            return {name: np.asarray(arr).reshape(-1) for name, arr in self.fields.items()}

        return {name: arr[:, self.probe_index] for name, arr in self.fields.items()}
