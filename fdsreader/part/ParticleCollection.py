from typing import Iterable, Dict, Sequence

from fdsreader.part import Particle
from fdsreader.utils import Mesh
from fdsreader.utils.data import FDSDataCollection
import fdsreader.utils.fortran_data as fdtype
from fdsreader import settings


class ParticleCollection(FDSDataCollection):
    """Collection of :class:`Plot3D` objects. Offers extensive functionality for filtering and
        using plot3Ds as well as its subclasses such as :class:`SubPlot3D`.
    """

    def __init__(self, times: Iterable[float], *particles: Iterable[Particle]):
        super().__init__(*particles)
        self.times = list(times)
        self._file_paths: Dict[Mesh, str] = dict()

        if settings.LAZY_LOAD:
            for particle in self:
                particle._init_callback = self._load_data

    def _post_init(self):
        if not settings.LAZY_LOAD:
            print("Test")
            self._load_data()

    def _load_data(self):
        """Function to read in all particle data for a simulation.
        """
        for mesh, file_path in self._file_paths.items():
            with open(file_path, 'rb') as infile:
                particles = self

                # Initial offset (ONE, fds version and number of particle classes)
                offset = 3 * fdtype.INT.itemsize
                # Number of quantities for each particle class (plus an INTEGER_ZERO)
                offset += fdtype.new((('i', 2),)).itemsize * len(particles)
                # 30-char long name and unit information for each quantity
                offset += fdtype.new((('c', 30),)).itemsize * 2 * sum(
                    [len(particle.quantities) for particle in particles])
                infile.seek(offset)

                for _ in self.times:
                    # Skip time value
                    infile.seek(fdtype.FLOAT.itemsize, 1)

                    # Read data for each particle class
                    for particle in particles:
                        # Read number of particles in each class
                        n_particles = fdtype.read(infile, fdtype.INT, 1)[0][0][0]

                        # Read positions
                        dtype_positions = fdtype.new((('f', 3 * n_particles),))
                        particle._positions.append(
                            fdtype.read(infile, dtype_positions, 1)[0][0].reshape(
                                (n_particles, 3), order='F').astype(float))

                        # Read tags
                        dtype_tags = fdtype.new((('i', n_particles),))
                        particle._tags.append(fdtype.read(infile, dtype_tags, 1)[0][0])

                        # Read actual quantity values
                        dtype_data = fdtype.new(
                            (('f', str((n_particles, len(particle.quantities)))),))
                        data_raw = fdtype.read(infile, dtype_data, 1)[0][0].reshape(
                            (n_particles, len(particle.quantities)), order='F')
                        for q, quantity in enumerate(particle.quantities):
                            particle._data[quantity.quantity].append(data_raw[:, q].astype(float))

    def __getitem__(self, key):
        if type(key) == int:
            return self._elements[key]
        for particle in self:
            if particle.class_name == key:
                return particle

    def __contains__(self, value):
        if value in self._elements:
            return True
        for particle in self:
            if particle.class_name == value:
                return True
        return False

    def __repr__(self):
        return "ParticleCollection(" + super(ParticleCollection, self).__repr__() + ")"
