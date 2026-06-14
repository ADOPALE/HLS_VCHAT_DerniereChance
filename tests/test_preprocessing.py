from optiflux.domain.models import Flow, ContainerType, VehicleType
from optiflux.data.preprocessing import create_units_for_day


def test_create_units_for_day_simple():
    flow = Flow("F1", 2, "A", "B", "Magasin", "Test", "Caisse", {"Lundi": 5}, 360, 480, "Propre", mixed_allowed=True)
    c = {"Caisse": ContainerType("Caisse", 0.5, 0.5, 0.01, 0.02)}
    v = {"VL": VehicleType("VL", "A", 2, 2, 2, 10, True, 1, 1, 1, {"Caisse"}, {"A", "B"})}
    units = create_units_for_day([flow], "Lundi", c, v)
    assert len(units) == 1
    assert next(iter(units.values())).quantity == 5
