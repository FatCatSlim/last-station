import json
import random
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

HUB_STATE_FILE = Path(__file__).parent / "hub_state.json"

# Power System Settings
POWER_CAPACITY = 100
MIN_INFRASTRUCTURE_POWER = 11
GENERATOR_DEGRADATION_MAX = 0.5
GENERATOR_DEGRADATION_MIN = 0.1

# Water and Food Storage Settings
WATER_TANK_CAPACITY = 100
FOOD_STORAGE_CAPACITY = 100

# Consumption and Production Rates
NORMAL_FOOD_CONSUMPTION = 2.0
RATION_FOOD_CONSUMPTION = 1.0
NORMAL_FOOD_PRODUCTION = 3.0

NORMAL_WATER_CONSUMPTION = 3.0
RATION_WATER_CONSUMPTION = 2.0
NORMAL_WATER_PRODUCTION = 4.0

# Expedition Duration
EXPEDITION_CYCLE_DURATION = 3
EXPEDITION_REWARDS = {
    "garden_7": {"food": 8, "water": 0, "power": 0, "scrap": 0},
    "sump_6": {"food": 0, "water": 10, "power": 0, "scrap": 0},
    "depot_14": {"food": 0, "water": 0, "power": 0, "scrap": 4},
}

# Generator Repair Settings
GENERATOR_REPAIR_RULES = {
    "minor": {"min_power": 51, "cycles": 2, "scrap": 4},
    "moderate": {"min_power": 11, "cycles": 3, "scrap": 6},
    "major": {"min_power": 1, "cycles": 4, "scrap": 8},
    "offline": {"min_power": 0, "cycles": 6, "scrap": 10},
}


def load_hub_state():
    with open(HUB_STATE_FILE, "r") as f:
        return json.load(f)


def save_hub_state(state):
    with open(HUB_STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


class HubHealthResponse(BaseModel):
    status: Literal["online", "offline"]  # only two possible values for status allowed
    hub_name: str
    hub_version: str


class HubInfoResponse(BaseModel):
    hub_name: str
    hub_version: str


class ResourceStatusResponse(BaseModel):
    cycle: int
    food: float
    water: float
    power: float
    scrap: int


class ResourceChange(BaseModel):
    food: float
    water: float
    power: float
    scrap: int


class CycleAdvanceRequest(BaseModel):
    action: Literal["normal", "ration"]


class ExpeditionDispatchRequest(BaseModel):
    location: Literal["garden_7", "sump_6", "depot_14"]


class ExpeditionDispatchResponse(BaseModel):
    status: str
    location: str | None
    cycle_remaining: int


# repair response model
class EngineeringResponse(BaseModel):
    detail: str
    status: Literal["available", "repairing"]
    cycle_remaining: int
    repair_target: float
    scrap: int


# infrastructure response models
class FarmInfrastructureResponse(BaseModel):
    status: Literal["online", "offline"]
    lights: Literal["online", "offline"]
    operational: bool


class WaterSystemResponse(BaseModel):
    source: Literal["available", "unavailable"]
    pump: Literal["online", "offline"]
    operational: bool


class PowerSystemResponse(BaseModel):
    wind_generators: Literal["online", "offline"]
    output: float
    operational: bool


class InfrastructureResponse(BaseModel):
    farm: FarmInfrastructureResponse
    water_system: WaterSystemResponse
    power_system: PowerSystemResponse


class CycleAdvanceResponse(BaseModel):
    action: Literal["normal", "ration"]
    resources: ResourceStatusResponse
    supply: ResourceChange
    consumption: ResourceChange
    power_degradation: float
    expedition: ExpeditionDispatchResponse
    expedition_reward: ResourceChange
    infrastructure: InfrastructureResponse
    engineering: EngineeringResponse


def get_consumption(action):
    if action == "ration":
        return {
            "food": RATION_FOOD_CONSUMPTION,
            "water": RATION_WATER_CONSUMPTION,
            "power": 0,
            "scrap": 0,
        }
    return {
        "food": NORMAL_FOOD_CONSUMPTION,
        "water": NORMAL_WATER_CONSUMPTION,
        "power": 0,
        "scrap": 0,
    }


# helper for power check
def get_current_power():
    if power_system_operational():
        return hub_state["infrastructure"]["power_system"]["output"]
    return 0


def power_system_operational():
    return bool(
        hub_state["infrastructure"]["power_system"]["wind_generators"] == "online"
        and hub_state["infrastructure"]["power_system"]["output"] > 0
    )


def water_system_operational():
    if (
        hub_state["infrastructure"]["water_system"]["source"] == "available"
        and hub_state["infrastructure"]["water_system"]["pump"] == "online"
        and get_current_power() >= MIN_INFRASTRUCTURE_POWER
    ):
        return True
    return False


def farm_system_operational():
    if (
        hub_state["infrastructure"]["farm"]["status"] == "online"
        and hub_state["infrastructure"]["farm"]["lights"] == "online"
        and water_system_operational()
        and get_current_power() >= MIN_INFRASTRUCTURE_POWER
    ):
        return True
    return False


def get_production_efficiency():
    if get_current_power() > 50:
        return 1.0
    elif get_current_power() >= 11:
        return 0.8
    else:
        return 0.0


def get_generator_degradation():
    degradation = round(
        random.uniform(GENERATOR_DEGRADATION_MIN, GENERATOR_DEGRADATION_MAX), 1
    )
    gen_output = round(get_current_power() - degradation, 1)
    if gen_output > 0:
        hub_state["infrastructure"]["power_system"]["output"] = gen_output
    else:
        hub_state["infrastructure"]["power_system"]["output"] = 0
    return degradation


# generator degradation and repair
def update_repair_status():
    if hub_state["engineering"]["status"] == "repairing":
        hub_state["engineering"]["cycle_remaining"] -= 1

        if hub_state["engineering"]["cycle_remaining"] <= 0:
            hub_state["infrastructure"]["power_system"]["output"] = hub_state[
                "engineering"
            ]["repair_target"]
            hub_state["engineering"]["status"] = "available"
            hub_state["engineering"]["cycle_remaining"] = 0
            hub_state["engineering"]["repair_target"] = 0

    return {
        "status": hub_state["engineering"]["status"],
        "cycle_remaining": hub_state["engineering"]["cycle_remaining"],
        "repair_target": hub_state["engineering"]["repair_target"],
    }


def start_generator_repair():
    if hub_state["engineering"]["status"] == "repairing":
        return "Repair already in progress"
    generator_output = hub_state["infrastructure"]["power_system"]["output"]
    scrap = hub_state["resources"]["scrap"]
    if generator_output >= POWER_CAPACITY:
        return "Generator does not need repair"

    if generator_output >= GENERATOR_REPAIR_RULES["minor"]["min_power"]:
        repair_cycles = GENERATOR_REPAIR_RULES["minor"]["cycles"]
        required_scrap = GENERATOR_REPAIR_RULES["minor"]["scrap"]
    elif generator_output >= GENERATOR_REPAIR_RULES["moderate"]["min_power"]:
        repair_cycles = GENERATOR_REPAIR_RULES["moderate"]["cycles"]
        required_scrap = GENERATOR_REPAIR_RULES["moderate"]["scrap"]
    elif generator_output >= GENERATOR_REPAIR_RULES["major"]["min_power"]:
        repair_cycles = GENERATOR_REPAIR_RULES["major"]["cycles"]
        required_scrap = GENERATOR_REPAIR_RULES["major"]["scrap"]
    else:
        repair_cycles = GENERATOR_REPAIR_RULES["offline"]["cycles"]
        required_scrap = GENERATOR_REPAIR_RULES["offline"]["scrap"]

    if scrap < required_scrap:
        return "Not enough scrap to start repair"
    hub_state["resources"]["scrap"] -= required_scrap
    repair_target = POWER_CAPACITY
    hub_state["engineering"]["status"] = "repairing"
    hub_state["engineering"]["cycle_remaining"] = repair_cycles
    hub_state["engineering"]["repair_target"] = repair_target
    return "Repair started"


app = FastAPI()  # create a api instance

hub_state = load_hub_state()
hub_resources = hub_state["resources"]


@app.get("/health", response_model=HubHealthResponse)  # get endpoint for health check
def health_check():
    return {"status": "online", "hub_name": "RAVEN-HUB", "hub_version": "0.1"}


@app.get("/hub-info", response_model=HubInfoResponse)  # get endpoint for hub info
def get_hub_info():
    return {"hub_name": "RAVEN-HUB", "hub_version": "0.1"}


@app.get(
    "/resources", response_model=ResourceStatusResponse
)  # get endpoint for resource status
def get_resources():
    hub_resources["power"] = get_current_power()
    return hub_resources


@app.get(
    "/expedition", response_model=ExpeditionDispatchResponse
)  # get endpoint for expedition status
def get_expedition():
    expedition = hub_state["expedition"]
    return expedition


@app.get(
    "/infrastructure", response_model=InfrastructureResponse
)  # get endpoint for infrastructure status
def get_infrastructure():
    infrastructure = hub_state["infrastructure"]
    return {
        "farm": {
            "status": infrastructure["farm"]["status"],
            "lights": infrastructure["farm"]["lights"],
            "operational": farm_system_operational(),
        },
        "water_system": {
            "source": infrastructure["water_system"]["source"],
            "pump": infrastructure["water_system"]["pump"],
            "operational": water_system_operational(),
        },
        "power_system": {
            "wind_generators": infrastructure["power_system"]["wind_generators"],
            "output": infrastructure["power_system"]["output"],
            "operational": power_system_operational(),
        },
    }


@app.get(
    "/engineering", response_model=EngineeringResponse
)  # get endpoint for engineering status
def get_engineering_status():
    return {
        "detail": "Engineering status",
        "status": hub_state["engineering"]["status"],
        "cycle_remaining": hub_state["engineering"]["cycle_remaining"],
        "repair_target": hub_state["engineering"]["repair_target"],
        "scrap": hub_state["resources"]["scrap"],
    }


@app.post("/expedition/dispatch", response_model=ExpeditionDispatchResponse)
def dispatch_expedition(request: ExpeditionDispatchRequest):
    expedition = hub_state["expedition"]
    if expedition["status"] != "idle":
        raise HTTPException(
            status_code=409, detail="Expedition team is already active."
        )
    expedition["status"] = "outbound"
    expedition["location"] = request.location
    expedition["cycle_remaining"] = EXPEDITION_CYCLE_DURATION
    save_hub_state(hub_state)
    return expedition


@app.post(
    "/engineering/repair", response_model=EngineeringResponse
)  # post endpoint for initiating repair
def repair_generator():
    repair_result = start_generator_repair()
    if repair_result == "Repair started":
        save_hub_state(hub_state)
    return {
        "detail": repair_result,
        "status": hub_state["engineering"]["status"],
        "cycle_remaining": hub_state["engineering"]["cycle_remaining"],
        "repair_target": hub_state["engineering"]["repair_target"],
        "scrap": hub_state["resources"]["scrap"],
    }


@app.post(
    "/advance-cycle", response_model=CycleAdvanceResponse
)  # post endpoint for advancing cycle
def advance_cycle(request: CycleAdvanceRequest):
    # simulate resource changes for the next cycle
    supply = {"food": 0.0, "water": 0.0, "power": 0, "scrap": 0}
    consumption = get_consumption(request.action)
    was_repairing = hub_state["engineering"]["status"] == "repairing"
    repair_status = update_repair_status()
    power_degradation = 0.0
    if repair_status["status"] == "available" and not was_repairing:
        power_degradation = get_generator_degradation()
    hub_resources["power"] = get_current_power()
    if water_system_operational():
        supply["water"] = round(
            max(0, NORMAL_WATER_PRODUCTION * get_production_efficiency()), 2
        )
    if farm_system_operational():
        supply["food"] = round(
            max(0, NORMAL_FOOD_PRODUCTION * get_production_efficiency()), 2
        )

    # rewards we get
    earned_expedition_reward = {"food": 0, "water": 0, "power": 0, "scrap": 0}

    hub_resources["cycle"] += 1
    hub_resources["food"] = round(
        min(
            FOOD_STORAGE_CAPACITY,
            hub_resources["food"] + supply["food"] - consumption["food"],
        ),
        2,
    )
    hub_resources["water"] = round(
        min(
            WATER_TANK_CAPACITY,
            hub_resources["water"] + supply["water"] - consumption["water"],
        ),
        2,
    )
    hub_resources["power"] = max(
        0, hub_resources["power"] + supply["power"] - consumption["power"]
    )
    hub_resources["scrap"] = max(
        0, hub_resources["scrap"] + supply["scrap"] - consumption["scrap"]
    )

    expedition = hub_state["expedition"]
    if expedition["status"] != "idle":
        expedition["cycle_remaining"] -= 1
        if expedition["cycle_remaining"] == 2:
            expedition["status"] = "gathering"
        elif expedition["cycle_remaining"] == 1:
            expedition["status"] = "returning"
        elif expedition["cycle_remaining"] <= 0:

            # remember the location before resetting it
            returned_location = expedition["location"]
            # add the expedition rewards to the hub resources
            rewards = EXPEDITION_REWARDS[returned_location]
            earned_expedition_reward = rewards

            hub_resources["food"] = min(
                FOOD_STORAGE_CAPACITY, hub_resources["food"] + rewards["food"]
            )
            hub_resources["water"] = min(
                WATER_TANK_CAPACITY, hub_resources["water"] + rewards["water"]
            )
            hub_resources["power"] += rewards["power"]
            hub_resources["scrap"] += rewards["scrap"]

            expedition["status"] = "idle"
            expedition["location"] = None
            expedition["cycle_remaining"] = 0
    hub_state["resources"] = hub_resources
    save_hub_state(hub_state)
    return {
        "action": request.action,
        "resources": hub_resources,
        "supply": supply,
        "consumption": consumption,
        "power_degradation": power_degradation,
        "expedition": {
            "status": expedition["status"],
            "location": expedition["location"],
            "cycle_remaining": expedition["cycle_remaining"],
        },
        "expedition_reward": earned_expedition_reward,
        "infrastructure": get_infrastructure(),
        "engineering": get_engineering_status(),
    }
