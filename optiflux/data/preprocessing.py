from __future__ import annotations

import math
import pandas as pd

from optiflux.config.columns import FLOW, SITE, VEHICLE, CONTAINER
from optiflux.config.defaults import DAY_QUANTITY_COLUMNS, DEFAULT_OCCUPANCY_RATE, SPECIAL_QUAY_CAPACITY, DEFAULT_QUAY_CAPACITY
from optiflux.domain.models import Site, VehicleType, ContainerType, Flow, TransportUnit
from optiflux.domain.ids import flow_id, unit_id
from optiflux.data.normalizer import normalize_bool, normalize_sanitary, normalize_exclusions
from optiflux.utils.time_utils import parse_time_to_min, parse_duration_to_min
from optiflux.capacity.capacity_checker import max_quantity_for_vehicle


def build_sites(df: pd.DataFrame, vehicle_type_names: list[str]) -> dict[str, Site]:
    sites: dict[str, Site] = {}
    for _, row in df.iterrows():
        name = str(row[SITE["name"]]).strip()
        compatible = {v for v in vehicle_type_names if normalize_bool(row.get(v), default=True)}
        sites[name] = Site(
            name=name,
            address=str(row.get(SITE["address"], "") or "").strip(),
            has_quay=normalize_bool(row.get(SITE["has_quay"]), default=True),
            quay_capacity=SPECIAL_QUAY_CAPACITY.get(name, DEFAULT_QUAY_CAPACITY),
            compatible_vehicle_types=compatible,
        )
    return sites


def build_containers(df: pd.DataFrame) -> dict[str, ContainerType]:
    containers: dict[str, ContainerType] = {}
    for _, row in df.iterrows():
        name = str(row[CONTAINER["name"]]).strip()
        containers[name] = ContainerType(
            name=name,
            length=float(row[CONTAINER["length"]]),
            width=float(row[CONTAINER["width"]]),
            empty_weight_t=float(row.get(CONTAINER["empty_weight"], 0) or 0),
            full_weight_t=float(row.get(CONTAINER["full_weight"], 0) or 0),
        )
    return containers


def build_vehicles(df: pd.DataFrame, sites_df: pd.DataFrame, occupancy_rate: float = DEFAULT_OCCUPANCY_RATE) -> dict[str, VehicleType]:
    vehicle_names = [str(v).strip() for v in df[VEHICLE["name"]].dropna()]
    site_compat: dict[str, set[str]] = {v: set() for v in vehicle_names}
    for _, row in sites_df.iterrows():
        site_name = str(row[SITE["name"]]).strip()
        for v in vehicle_names:
            if normalize_bool(row.get(v), default=True):
                site_compat[v].add(site_name)

    vehicles: dict[str, VehicleType] = {}
    container_cols = [c for c in df.columns if c not in set(VEHICLE.values())]
    for _, row in df.iterrows():
        name = str(row[VEHICLE["name"]]).strip()
        compatible_containers = {str(c).strip() for c in container_cols if normalize_bool(row.get(c), default=False)}
        vehicles[name] = VehicleType(
            name=name,
            initial_site=str(row[VEHICLE["initial_site"]]).strip(),
            length=float(row[VEHICLE["length"]]),
            width=float(row[VEHICLE["width"]]),
            height=float(row[VEHICLE["height"]]) if pd.notna(row.get(VEHICLE["height"])) else None,
            payload_t=float(row[VEHICLE["payload"]]),
            has_lift=normalize_bool(row.get(VEHICLE["has_lift"]), default=False),
            dock_time_min=float(parse_duration_to_min(row.get(VEHICLE["dock_time"]), 0) or 0),
            handling_no_quay_min_per_container=float(parse_duration_to_min(row.get(VEHICLE["handling_no_quay"]), 0) or 0),
            handling_with_quay_min_per_container=float(parse_duration_to_min(row.get(VEHICLE["handling_with_quay"]), 0) or 0),
            compatible_containers=compatible_containers,
            compatible_sites=site_compat.get(name, set()),
            cost_per_km=float(row.get(VEHICLE["cost_km"], 0) or 0),
            carbon_per_km=float(row.get(VEHICLE["carbon_km"], 0) or 0),
            occupancy_rate=occupancy_rate,
        )
    return vehicles


def build_flows(df: pd.DataFrame) -> list[Flow]:
    flows: list[Flow] = []
    for idx, row in df.iterrows():
        row_no = int(idx) + 2
        origin = str(row[FLOW["origin"]]).strip()
        dest = str(row[FLOW["destination"]]).strip()
        support = str(row.get(FLOW["support_function"], "") or "").strip()
        fid = flow_id(row_no, support, origin, dest)
        qty_by_day: dict[str, int] = {}
        for day, col in DAY_QUANTITY_COLUMNS.items():
            try:
                qty_by_day[day] = int(float(row.get(col, 0) or 0))
            except Exception:
                qty_by_day[day] = 0
        mut = normalize_bool(row.get(FLOW["mutualized"]), default=False)
        mut_name = str(row.get(FLOW["mutualized_name"], "") or "").strip() if mut else ""
        flows.append(Flow(
            id=fid,
            row_number=row_no,
            origin=origin,
            destination=dest,
            support_function=support,
            nature=str(row.get(FLOW["nature"], "") or "").strip(),
            container_name=str(row.get(FLOW["container"], "") or "").strip(),
            quantity_by_day=qty_by_day,
            pickup_min=parse_time_to_min(row.get(FLOW["pickup_min"])),
            delivery_max=parse_time_to_min(row.get(FLOW["delivery_max"])),
            sanitary=normalize_sanitary(row.get(FLOW["sanitary"])),
            full_empty=str(row.get(FLOW["full_empty"], "") or "").strip(),
            mixed_allowed=normalize_bool(row.get(FLOW["mixed"]), default=False),
            exclusions=normalize_exclusions(row.get(FLOW["exclusions"])),
            mutualized_name=mut_name or None,
            original=row.to_dict(),
        ))
    return flows


def active_flows_for_day(flows: list[Flow], day: str, support_filter: list[str] | None = None) -> list[Flow]:
    support_filter = support_filter or []
    result = []
    for flow in flows:
        if flow.quantity_by_day.get(day, 0) <= 0:
            continue
        if support_filter and flow.support_function not in support_filter:
            continue
        result.append(flow)
    return result


def compatible_vehicle_names(flow: Flow, vehicles: dict[str, VehicleType]) -> list[str]:
    names = []
    for name, vt in vehicles.items():
        if flow.container_name not in vt.compatible_containers:
            continue
        if flow.origin not in vt.compatible_sites or flow.destination not in vt.compatible_sites:
            continue
        names.append(name)
    return names


def split_flows_into_units(day_flows: list[Flow], containers: dict[str, ContainerType], vehicles: dict[str, VehicleType]) -> dict[str, TransportUnit]:
    units: dict[str, TransportUnit] = {}
    for flow in day_flows:
        if flow.pickup_min is None or flow.delivery_max is None:
            continue
        container = containers[flow.container_name]
        candidates = [vehicles[n] for n in compatible_vehicle_names(flow, vehicles)]
        candidates = sorted(candidates, key=lambda v: (v.usable_floor_area, v.payload_t), reverse=True)
        qty = flow.quantity_by_day.get(next(iter(flow.quantity_by_day.keys())), 0)
        # La quantité réelle du jour est réinjectée juste après via original; cette fonction est appelée par helper dédié ci-dessous.
    return units


def create_units_for_day(day_flows: list[Flow], day: str, containers: dict[str, ContainerType], vehicles: dict[str, VehicleType]) -> dict[str, TransportUnit]:
    units: dict[str, TransportUnit] = {}
    for flow in day_flows:
        qty_total = int(flow.quantity_by_day.get(day, 0))
        if qty_total <= 0 or flow.pickup_min is None or flow.delivery_max is None:
            continue
        container = containers[flow.container_name]
        candidates = [vehicles[n] for n in compatible_vehicle_names(flow, vehicles)]
        candidates = sorted(candidates, key=lambda v: (v.usable_floor_area, v.payload_t), reverse=True)
        if not candidates:
            continue
        largest = candidates[0]
        max_qty = max_quantity_for_vehicle(container, largest, qty_total)
        if max_qty <= 0:
            continue
        full_units = qty_total // max_qty
        remainder = qty_total % max_qty
        idx = 1
        for _ in range(full_units):
            uid = unit_id(flow.id, idx)
            units[uid] = TransportUnit(
                id=uid,
                source_flow_ids=[flow.id],
                row_numbers=[flow.row_number],
                origin=flow.origin,
                destination=flow.destination,
                support_function=flow.support_function,
                nature=flow.nature,
                container_name=flow.container_name,
                quantity=max_qty,
                pickup_min=flow.pickup_min,
                delivery_max=flow.delivery_max,
                sanitary=flow.sanitary,
                mixed_allowed=flow.mixed_allowed,
                exclusions=set(flow.exclusions),
                mutualized_group=flow.mutualized_name,
                preferred_vehicle_type=largest.name,
                groupable=False if flow.mutualized_name else True,
            )
            idx += 1
        if remainder > 0 or qty_total < max_qty:
            q = remainder if remainder > 0 else qty_total
            uid = unit_id(flow.id, idx)
            units[uid] = TransportUnit(
                id=uid,
                source_flow_ids=[flow.id],
                row_numbers=[flow.row_number],
                origin=flow.origin,
                destination=flow.destination,
                support_function=flow.support_function,
                nature=flow.nature,
                container_name=flow.container_name,
                quantity=q,
                pickup_min=flow.pickup_min,
                delivery_max=flow.delivery_max,
                sanitary=flow.sanitary,
                mixed_allowed=flow.mixed_allowed,
                exclusions=set(flow.exclusions),
                mutualized_group=flow.mutualized_name,
                preferred_vehicle_type=None,
                groupable=True,
            )
    return units
