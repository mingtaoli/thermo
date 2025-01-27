# Changelog

## [Unreleased]

### Added

### Changed

### Removed

### Fixed

## [0.2.26] - 2023-09-17

### Changed
- Previously added accurate fits to pure-component temperature-dependent properties now have analytical integrals implemented so as to speed up enthalpy and entropy calculations.
- Creation of Flasher objects has been sped up
- Add some fits for pure metal solid and liquid heat capacities to the SGTE UNARY database. The fits are quite accurate but do not implement the same equations.
- Add base class for ThermalConductivitySolid
- Add element fits for thermal conductivities of solids from the source: Ho, C. Y., R. W. Powell, and P. E. Liley. "Thermal Conductivity of the Elements." Journal of Physical and Chemical Reference Data 1, no. 2 (April 1, 1972): 279-421. https://doi.org/10.1063/1.3253100.
- Add additional data for sublimation pressure
- Fix an issue with threading and sqlite lookups

## [0.2.25] - 2023-06-04

### Changed
- Code cleanup with ruff (experiment)
- Add accurate fits to pure-component temperature-dependent properties derived using REFPROP. This is the preferred method where available. As part of this effort, a way of adding new data to thermo using json files is being experimented with.
- Add liquid density and viscosity correlation for 8 elements (experiment)