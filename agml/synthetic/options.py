# Copyright 2021 UC Davis Plant AI and Biophysics Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from typing import List
from numbers import Number
from dataclasses import dataclass

import numpy as np

from agml.framework import AgMLSerializable
from agml.synthetic.config import load_default_helios_configuration


@dataclass
class Parameters:
    """Base class for parameters, to enable runtime type checks."""
    def __post_init__(self):
        self._block_new_attributes = True

    def __setattr__(self, key, value):
        # Don't allow the assignment of new attributes.
        if key not in self.__dict__.keys():
            if not hasattr(self, '_block_new_attributes'):
                super().__setattr__(key, value)
                return
            raise AttributeError(f"Cannot assign new attributes '{key}' "
                                 f"to class {self.__class__.__name__}.")

        # Check if the type of the value matches that of the key.
        annotation = self.__annotations__[key]
        if not isinstance(value, annotation):
            raise TypeError(
                f"Expected a value of type ({annotation}) for attribute "
                f"'{key}', instead got '{value}' of type ({type(value)}).")
        super().__setattr__(key, value)


@dataclass
class CanopyParameters(Parameters):
    """Stores canopy-specific parameters for Helios."""
    leaf_length: Number                = None
    leaf_width: Number                 = None
    leaf_size: Number                  = None
    leaf_subdivisions: List[Number]    = None
    leaf_texture_file: str             = None
    leaf_color: str                    = None
    leaf_angle_distribution: str       = None
    leaf_area_index: Number            = None
    leaf_area_density: Number          = None
    leaf_spacing_fraction: Number      = None
    stem_color: List[Number]           = None
    stem_subdivisions: Number          = None
    stems_per_plant: Number            = None
    stem_radius: Number                = None
    plant_height: Number               = None
    grape_radius: Number               = None
    grape_color: List[Number]          = None
    grape_subdivisions: Number         = None
    fruit_color: List[Number]          = None
    fruit_radius: Number               = None
    fruit_subdivisions: Number         = None
    fruit_texture_file: os.PathLike    = None
    wood_texture_file: os.PathLike     = None
    wood_subdivisions: Number          = None
    clusters_per_stem: Number          = None
    plant_spacing: Number              = None
    row_spacing: Number                = None
    level_spacing: Number              = None
    plant_count: List[Number]          = None
    canopy_origin: List[Number]        = None
    canopy_rotation: Number            = None
    canopy_height: Number              = None
    canopy_extent: List[Number]        = None
    canopy_configuration: str          = None
    base_height: Number                = None
    crown_radius: Number               = None
    cluster_radius: Number             = None
    cluster_height_max: Number         = None
    trunk_height: Number               = None
    trunk_radius: Number               = None
    cordon_height: Number              = None
    cordon_radius: Number              = None
    cordon_spacing: Number             = None
    shoot_length: Number               = None
    shoot_radius: Number               = None
    shoots_per_cordon: Number          = None
    shoot_angle: Number                = None
    shoot_angle_tip: Number            = None
    shoot_angle_base: Number           = None
    shoot_color: List[Number]          = None
    shoot_subdivisions: List[Number]   = None
    needle_width: Number               = None
    needle_length: Number              = None
    needle_color: List[Number]         = None
    needle_subdivisions: List[Number]  = None
    branch_length: Number              = None
    branches_per_level: Number         = None
    buffer: str                        = None


@dataclass
class CameraParameters(Parameters):
    """Stores camera parameters for Helios."""
    image_resolution: List[Number]  = None
    camera_position: List[Number]   = None
    camera_lookat: List[Number]     = None


@dataclass
class LiDARParameters(Parameters):
    """Stores LiDAR parameters for Helios."""
    origin: List[Number]    = None
    size: List[Number]      = None
    thetaMin: Number        = None
    thetaMax: Number        = None
    phiMin: Number          = None
    phiMax: Number          = None
    exitDiameter: Number    = None
    beamDivergence: Number  = None
    ASCII_format: str       = None


class HeliosOptions(AgMLSerializable):
    """Stores a set of parameter options for a `HeliosDataGenerator`.

    The primary exposed options are the `canopy_parameters` (as well as similar
    options for camera position and LiDAR, `camera/lidar_parameters' specifically),
    as well as the `canopy_parameter_ranges` (as well as a similar set of options
    for camera and LiDAR, once again).

    The `HeliosOptions` is instantiated with the name of the canopy type that you
    want to generate; from there, the parameters and ranges can be accessed through
    properties, which are set to their default values as loaded from the Helios
    configuration upon instantiating the class.

    This `HeliosOptions` object, once configured, can then be passed directly to
    a `HeliosDataGenerator` upon instantiation, and be used to generate synthetic
    data according to its specification. The options can be edited and then the
    generation process run again to obtain a new set of data.

    Parameters
    ----------
    canopy : str
        The type of plant canopy to be used in generation.
    """
    serializable = frozenset(('canopy', 'canopy_parameters',
                              'camera_parameters', 'lidar_parameters'))

    # The default configuration parameters are loaded directly from
    # the `helios_config.json` file which is constructed each time
    # Helios is installed or updated.
    _default_config = load_default_helios_configuration()

    def __init__(self, canopy = None):
        # Check that the provided canopy is valid.
        self._initialize_canopy(canopy)

    def _initialize_canopy(self, canopy):
        """Initializes Helios options from the provided canopy."""
        if canopy not in self._default_config['canopy']['types']:
            raise ValueError(
                f"Received invalid canopy type '{canopy}', expected "
                f"one of: {self._default_config['canopy']['types']}.")
        self._canopy = canopy

        # Get the parameters and ranges corresponding to the canopy type.
        print(self._default_config['canopy']['parameters'][canopy])
        self._canopy_parameters = \
            CanopyParameters(**self._default_config['canopy']['parameters'][canopy])
        self._camera_parameters = \
            CameraParameters(**self._default_config['camera']['parameters'])
        self._lidar_parameters = \
            LiDARParameters(**self._default_config['lidar']['parameters'])

    @property
    def canopy(self) -> CanopyParameters:
        return self._canopy_parameters

    @property
    def camera(self) -> CameraParameters:
        return self._camera_parameters

    @property
    def lidar(self) -> LiDARParameters:
        return self._lidar_parameters

    def reset(self):
        """Resets the parameters to the default for the canopy."""
        self._initialize_canopy(self._canopy)


