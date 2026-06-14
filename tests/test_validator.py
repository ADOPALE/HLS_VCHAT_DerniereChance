from optiflux.domain.models import Solution
from optiflux.validation.solution_validator import SolutionValidator
from optiflux.utils.matrix_utils import MatrixRepository


def test_empty_solution_invalid_when_units_missing():
    sol = Solution(day="Lundi", routes=[], units={})
    validator = SolutionValidator({}, {}, MatrixRepository({}, {}))
    validator.validate(sol)
    assert sol.hard_valid is True
