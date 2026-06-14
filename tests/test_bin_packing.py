from optiflux.domain.models import ContainerType, VehicleType
from optiflux.capacity.bin_packing import shelf_pack_2d, effective_footprints
from optiflux.capacity.capacity_checker import can_quantity_fit


def vehicle():
    return VehicleType("VL", "HSJ", 2.0, 2.0, 2.0, 1.0, True, 5, 1, 1, {"Caisse test", "Roll"}, {"HSJ"}, occupancy_rate=0.85)


def test_caisse_stack_by_three():
    c = ContainerType("Caisse test", 1, 1, 0.01, 0.02)
    assert effective_footprints(c, 7) == 3


def test_non_stackable():
    c = ContainerType("Roll", 1, 1, 0.01, 0.02)
    assert effective_footprints(c, 7) == 7


def test_rotation_possible():
    c = ContainerType("Roll", 2.0, 1.0, 0.01, 0.02)
    assert shelf_pack_2d(c, vehicle(), 1).feasible


def test_weight_blocks():
    c = ContainerType("Caisse test", 0.1, 0.1, 0.01, 2.0)
    assert not can_quantity_fit(c, vehicle(), 1)
