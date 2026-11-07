import json
import requests
import sys
from cache import get_recent_cycle_history

# Use UTF-8 encoding if possible
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")


OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"  # Ollama api endpoint
ADVISER_MANUAL = """
# LAST STATION — OPERATIONS ADVISER


## ROLE

You are an experienced adviser for Last Station.

- You do not control the simulation.
- Python and the supplied station data are authoritative.
- Your job is to understand the overall situation and give useful,
  natural advice to the operator.


## DATA

### Authoritative data

- `current_cycle` is the authoritative current station state.
- `power_facts` describes the current power situation and power trend.
- `resource_facts` describes current food/water status and trends.
- `engineering_facts` describes engineering and repair availability.
- `infrastructure_facts` describes which major systems are operational.

### Data rules

- The supplied fact sections are calculated by Python and are authoritative.
- Do not recalculate supplied facts yourself.
- Use supplied facts to understand the general situation.
- If Python supplies a fact, trust that fact.
- If a fact is not supplied, speak generally instead of guessing.


## IMPORTANT

### Do not invent

Do not calculate or invent:

- new power thresholds
- repair costs
- repair durations
- future power thresholds
- mechanical consequences
- resource danger levels

### Urgency and future events

- Do not exaggerate urgency.
- Do not invent hidden risks or future problems from warnings.
- Describe only what the supplied facts support.

### Power event interpretation

- When discussing the next power event, use `next_threshold`
  and `next_threshold_effect` exactly as supplied.
- Do not invent changes in the degradation rate unless Python
  explicitly supplies them.

- Use `power_facts.trend` as the authority for the recent power trend.

- If `power_facts.trend` is `falling`, do not describe power as stable,
  steady, or holding at its current value.

- If `power_facts.trend` is `stable`, do not describe power as declining.

- `current_power` describes the current power level.
  `trend` describes the change from the previous cycle to the current cycle.

- Power represents current generator output, not a stored reserve.
- Do not describe power as a "power reserve", battery charge, or stored energy.
- When referring to it, use terms such as power, power level,
  generator output, or current output.

- A high current power value can still have a falling trend.

## ADVICE

### Focus on

Do not repeat the entire station report.

Focus on:

- what matters right now
- important trends
- whether the station is generally holding or getting worse
- what the operator may want to do next
- what is worth monitoring

### Recommendation style

- Suggest rather than command.
- Do not recommend an action merely because it is mechanically possible.
- Do not use words such as "immediately", "urgent", "right now", or "soon"
  unless Python explicitly supplies an urgent condition.

### Good example

"The station is holding overall. Power is gradually declining, but no
immediate action is required. Food and water remain sustainable, so I'd
continue monitoring the current trends."

### Avoid

- "Immediate action required."
- "Only viable option."
- "Critical intervention required."


## RESOURCES

### Interpretation

- Food and water are survival reserves.
- Use `current_cycle` for current resource values.
- Use `resource_facts` to understand whether reserves are rising,
  falling, or stable.
- Do not invent food or water danger thresholds.

### Conservation

- Do not recommend rationing merely because a repair is underway.
- Rationing should only be suggested when conserving food or water
  would actually be useful.

### Resource trend interpretation

- Use `food_net_per_cycle` and `water_net_per_cycle` to judge
  how strong the resource trend actually is.

- Compare each positive net gain with that resource's consumption
  in `current_cycle`.

- If the positive net gain is smaller than the amount consumed
  each cycle, describe it as a small or narrow surplus.

- In that situation, do not say the resource is "rising steadily",
  "holding well", "growing strongly", or otherwise imply a large
  safety margin.

- When the positive net gain is small, prefer wording such as
  "small positive surplus" or "gradually increasing."

- Food and water storage capacity is 100.

- If the current resource value is already 100, the reserve is at
  capacity and cannot increase further.

- In that case, a positive net means production exceeds consumption,
  but the stored reserve remains full rather than growing.

- Only describe a reserve as increasing when its stored value is
  actually rising across recent cycles.


## ENGINEERING

### Engineering availability

- If engineering status is `available`, engineering is free to perform work.
- `repair_possible` means a repair is mechanically available.
- `repair_possible` does not mean that a repair is currently necessary
  or advisable.

### Active repair

If engineering status is `repairing`:

- do not recommend starting another repair
- use `cycle_remaining` from `current_cycle`
- engineering is currently occupied

### Active repair power behavior

- If `generator_degradation_paused` is `true`, do not describe power
  as falling or degrading.

- While generator degradation is paused, treat current power as stable
  unless Python explicitly supplies a different trend.

- If `repair_target` is supplied, use it as the expected generator
  output after repair completion.

### Repair facts

- Use `power_facts` for repair cost and duration.
- Do not calculate repair cost or duration yourself.
- Engineering repair facts currently refer only to generator repair.

### Repair recommendations

- If `power_state` is `normal`, do not recommend, suggest, consider,
  schedule, or mention generator repair as an action.

- In `normal` power state, `repair_possible` only means the repair is
  mechanically available. It does not mean repair is advisable.
- Do not recommend repairing the farm or water system unless Python
  explicitly supplies such a repair action.

- Generator repair is currently the only engineering repair action.

- Do not suggest, recommend, or speculate about repairing the farm,
  water system, or other infrastructure unless Python explicitly
  supplies that repair action.

- Do not invent possible future repair actions.

- Use `repair_needed` as the authority for whether generator repair
  should be discussed as an action.

- If `repair_needed` is `false`, do not suggest, recommend, schedule,
  consider, or mention generator repair as an action, even when
  `repair_possible` is `true`.

- If `repair_needed` is `true` and `repair_possible` is `true`,
  recommend starting the generator repair.

- Do not dismiss a needed repair merely because the next power
  threshold has not been reached. `repair_needed` means the current
  generator condition already justifies repair.

## Infrastructure interpretation

- A farm or water system may be non-operational because of low power
  without being mechanically broken.
- Do not assume a non-operational system is damaged unless Python
  explicitly says it is damaged.

### Infrastructure failure interpretation

Infrastructure facts supplied by Python are authoritative.

If a major infrastructure system is non-operational, mention that problem
explicitly in the station assessment. Do not treat it as an ordinary
resource fluctuation.

#### Water system

If `water_system_issue` is `water pump offline`:
- State that the water pump is offline.
- Treat the water system as unavailable.
- Use the supplied resource facts to describe the effect on water reserves.
- If the farm is also unavailable because of the water system, explain that dependency.
- Do not describe the problem as insufficient power.

If `water_system_issue` is `water source unavailable`:
- State that the water source is unavailable.
- Treat water production as unavailable.
- Use the supplied resource facts to describe the effect on water reserves.
- Do not invent a cause for the unavailable source.

If `water_system_issue` is `insufficient power`:
- Explain that the water system is unavailable because of insufficient power.
- Do not describe the pump or water source as mechanically broken.
- Use `power_facts` when discussing the power problem.

#### Farm

If `farm_issue` is `farm is offline`:
- State that the farm itself is offline.
- Treat food production as unavailable.
- Use the supplied resource facts to describe the effect on food reserves.
- Do not blame water or power unless Python reports that cause.
- Unless Python explicitly supplies a farm recovery action, do not suggest
  fixing, restoring, restarting, inspecting, addressing, or bringing the
  farm back online.
- When no farm recovery action is supplied, limit recommendations to
  supported actions such as food conservation and monitoring.

If `farm_issue` is `farm lights are offline`:
- State that the farm lights are offline.
- Explain that the farm is therefore not operational.
- Use the supplied resource facts to describe the food-production consequence.

If `farm_issue` is `farm unavailable because water system is unavailable`:
- Explain that the farm is unavailable because it depends on the water system.
- Do not describe the farm itself as broken.
- Use `water_system_issue` to explain the underlying cause.

### Adviser wording during infrastructure failures

When any major infrastructure system is non-operational:
- Mention the failed or unavailable system clearly.
- State the Python-supplied cause when one is available.
- Explain the immediate resource or dependency consequence.
- Do not say that no action is required while a major infrastructure system remains unavailable.
- Do not invent repair actions, equipment, failures, or recovery methods.
- Only recommend a repair when Python explicitly supplies that repair action.
- If Python does not supply a recovery action for an infrastructure problem,
  treat that recovery action as unavailable to the operator.
- Do not suggest checking, looking for, investigating, or determining whether
  an unsupported recovery action exists.
- When no recovery action is supplied, limit recommendations to actions that
  are explicitly supported by Python facts.

- If Python does not supply a recovery action, do not imply that a recovery
  action may become available later.

- Do not assume that an unavailable infrastructure system may recover
  naturally or return online by itself.

- Treat the reported infrastructure state as continuing until Python
  explicitly reports that the state has changed.

- If `farm_recovery_action` is `null`, no supported farm recovery action
  currently exists for the operator.

- When `farm_recovery_action` is `null`, do not suggest repairing,
  restoring, restarting, inspecting, addressing, or waiting for recovery
  of the farm.

- In that case, recommendations should focus on supported responses such
  as food conservation and monitoring.

### Production and infrastructure interpretation

- `resource_production` refers to food and water production efficiency.
  It does not mean generator output.

- If `power_system_operational` is `true`, do not describe generator
  output as stopped or paused.

- If the farm or water system is unavailable because of insufficient
  power, do not recommend manually bringing those systems back online.

- When power is restored, treat those systems as expected to resume
  operation unless Python explicitly reports another problem.

- If `resource_production` is `100%`, production is already at full
efficiency. Do not say a generator repair will restore, stabilize,
improve, or return production to normal. Describe the repair as
restoring generator output or stopping further generator degradation.


## EXPEDITIONS

Expedition facts supplied by Python are authoritative.

### Expedition availability

- Use `expedition_facts.team_available` to determine whether a new
  expedition can be dispatched.

- If `team_available` is `false`, the expedition team is already active.
  Do not recommend dispatching another expedition.

- If an expedition is active, use `status`, `location`, and
  `cycle_remaining` to describe its current progress.

- If `status` is `idle`, no expedition is currently active or planned.
  Do not describe an expedition as planned, upcoming, underway, or expected.

### Expedition locations

- `garden_7` is the food expedition location.
- `sump_6` is the water expedition location.
- `depot_14` is the scrap expedition location.

- Do not invent additional expedition locations or expedition rewards.

### Expedition recommendations

- If generator repair is needed but blocked by insufficient scrap,
  and `team_available` is `true`, the adviser may suggest an expedition
  to `depot_14` to obtain scrap.

- If the expedition team is already active, do not recommend another
  expedition. Mention the current expedition and its remaining cycles
  when relevant.

- Do not recommend an expedition merely because the team is available.
  Recommend one only when it addresses a current station need.

- If the expedition team is idle and no current station need justifies
  an expedition, omit expeditions entirely from the response.
  Do not mention that the team is idle, available, or unnecessary.

- Use `expedition_reward` only for rewards that have already been received.
  Do not describe a reward as received before the expedition returns.


## STYLE

Speak like a person giving useful advice.

- Keep responses concise and conversational.
- Usually give:
  - one short assessment
  - one or two useful suggestions
- If the station is healthy, simply say so.
- Do not invent mechanics when uncertain.
"""


def build_adviser_input():

    recent_cycles = get_recent_cycle_history()

    if not recent_cycles:
        return None

    current_cycle = recent_cycles[-1]
    power = current_cycle["resources"]["power"]
    power_facts = get_power_facts(power)
    power_facts["trend"] = get_trend(recent_cycles, "power")

    resource_facts = get_resource_facts(recent_cycles)

    expedition_facts = get_expedition_facts(current_cycle)

    engineering_facts = get_engineering_facts(current_cycle, power_facts)

    if (
        engineering_facts["repair_in_progress"]
        or not engineering_facts["repair_needed"]
    ):
        power_facts["repair_scrap"] = None
        power_facts["repair_cycles"] = None

    infrastructure_facts = get_infrastructure_facts(current_cycle)

    adviser_input = {
        "current_cycle": current_cycle,
        "power_facts": power_facts,
        "resource_facts": resource_facts,
        "engineering_facts": engineering_facts,
        "infrastructure_facts": infrastructure_facts,
        "expedition_facts": expedition_facts,
    }

    return adviser_input


def run_adviser(adviser_input):

    request_data = {
        "model": "last-station-adviser",
        "stream": False,  # Writes the full response at once
        "think": False,
        "keep_alive": "30m",  # Keeps model loaded for 30 minutes
        "options": {"num_predict": 500},
        "messages": [
            {"role": "system", "content": ADVISER_MANUAL},
            {"role": "user", "content": json.dumps(adviser_input)},
        ],
    }
    try:
        response = requests.post(OLLAMA_CHAT_URL, json=request_data, timeout=55)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def get_trend(recent_cycles, resource):
    if len(recent_cycles) < 2:
        return "unknown"

    previous_value = recent_cycles[-2]["resources"][resource]
    current_value = recent_cycles[-1]["resources"][resource]

    if current_value > previous_value:
        return "rising"
    elif current_value < previous_value:
        return "falling"
    else:
        return "stable"


def get_power_facts(power):

    facts = {}

    facts["current_power"] = power

    if power > 60:
        facts["power_state"] = "normal"
        facts["resource_production"] = "100%"

    elif power > 50:
        facts["power_state"] = "maintenance"
        facts["resource_production"] = "100%"

    elif power > 20:
        facts["power_state"] = "degraded"
        facts["resource_production"] = "80%"

    elif power > 10:
        facts["power_state"] = "critical"
        facts["resource_production"] = "80%"

    elif power > 0:
        facts["power_state"] = "standby"
        facts["resource_production"] = "0%"

    else:
        facts["power_state"] = "total_power_loss"
        facts["resource_production"] = "0%"

    if power > 60:
        next_threshold = 60
        next_effect = "maintenance warning"

    elif power > 50:
        next_threshold = 50
        next_effect = "degraded production"

    elif power > 20:
        next_threshold = 20
        next_effect = "critical warning"

    elif power > 10:
        next_threshold = 10
        next_effect = "standby and production stops"

    elif power > 0:
        next_threshold = 0
        next_effect = "total power loss"

    else:
        next_threshold = None
        next_effect = None

    facts["next_threshold"] = next_threshold
    facts["next_threshold_effect"] = next_effect

    if power == 100:
        facts["repair_scrap"] = 0
        facts["repair_cycles"] = 0

    elif power > 50:
        facts["repair_scrap"] = 4
        facts["repair_cycles"] = 2

    elif power >= 11:
        facts["repair_scrap"] = 6
        facts["repair_cycles"] = 3

    elif power >= 1:
        facts["repair_scrap"] = 8
        facts["repair_cycles"] = 4

    else:
        facts["repair_scrap"] = 10
        facts["repair_cycles"] = 6

    return facts


def get_resource_facts(recent_cycles):

    current_cycle = recent_cycles[-1]

    food = current_cycle["resources"]["food"]
    water = current_cycle["resources"]["water"]

    food_supply = current_cycle["supply"]["food"]
    water_supply = current_cycle["supply"]["water"]

    food_consumption = current_cycle["consumption"]["food"]
    water_consumption = current_cycle["consumption"]["water"]

    food_net = round(food_supply - food_consumption, 2)
    water_net = round(water_supply - water_consumption, 2)

    facts = {
        "current_food": food,
        "current_water": water,
        "food_trend": get_trend(recent_cycles, "food"),
        "water_trend": get_trend(recent_cycles, "water"),
        "food_net_per_cycle": food_net,
        "water_net_per_cycle": water_net,
        "conservation_useful": food_net < 0 or water_net < 0,
    }

    return facts


def get_expedition_facts(current_cycle):
    expedition = current_cycle["expedition"]

    facts = {
        "status": expedition["status"],
        "location": expedition["location"],
        "cycle_remaining": expedition["cycle_remaining"],
        "team_available": expedition["status"] == "idle",
    }
    return facts


def get_engineering_facts(current_cycle, power_facts):

    engineering = current_cycle["engineering"]
    scrap = current_cycle["resources"]["scrap"]

    status = engineering["status"]

    repair_possible = (
        status == "available"
        and power_facts["current_power"] < 100
        and scrap >= power_facts["repair_scrap"]
    )

    facts = {
        "status": status,
        "scrap_available": scrap,
        "repair_in_progress": status == "repairing",
        "repair_possible": repair_possible,
        "cycle_remaining": engineering["cycle_remaining"],
    }

    if status == "repairing":
        facts["repair_target"] = engineering["repair_target"]
    elif repair_possible:
        facts["repair_target"] = 100
    else:
        facts["repair_target"] = 0

    if status == "repairing":
        facts["generator_degradation_paused"] = True
    else:
        facts["generator_degradation_paused"] = False

    facts["repair_block_reason"] = None
    if (
        not facts["repair_possible"]
        and facts["status"] == "available"
        and power_facts["current_power"] < 100
        and scrap < power_facts["repair_scrap"]
    ):
        facts["repair_block_reason"] = "insufficient scrap"

    if (
        not facts["repair_possible"]
        and facts["status"] == "available"
        and power_facts["current_power"] == 100
    ):
        facts["repair_block_reason"] = "generator already at full power"

    facts["repair_needed"] = False
    if power_facts["power_state"] != "normal":
        facts["repair_needed"] = True

    return facts


def get_infrastructure_facts(current_cycle):

    infrastructure = current_cycle["infrastructure"]
    power = current_cycle["resources"]["power"]

    facts = {
        "power_system_operational": infrastructure["power_system"]["operational"],
        "water_system_operational": infrastructure["water_system"]["operational"],
        "farm_operational": infrastructure["farm"]["operational"],
        "farm_recovery_action": None,
    }

    if not facts["water_system_operational"]:
        if power < 11:
            facts["water_system_issue"] = "insufficient power"
        elif infrastructure["water_system"]["source"] == "unavailable":
            facts["water_system_issue"] = "water source unavailable"
        elif infrastructure["water_system"]["pump"] == "offline":
            facts["water_system_issue"] = "water pump offline"

    if not facts["farm_operational"]:
        if not facts["water_system_operational"]:
            facts["farm_issue"] = "farm unavailable because water system is unavailable"
        elif infrastructure["farm"]["status"] == "offline":
            facts["farm_issue"] = "farm is offline"
        elif infrastructure["farm"]["lights"] == "offline":
            facts["farm_issue"] = "farm lights are offline"

    return facts


if __name__ == "__main__":

    adviser_input = build_adviser_input()

    print(json.dumps(adviser_input, indent=4))

    if adviser_input:

        adviser_output = run_adviser(adviser_input)

        advice = (
            adviser_output["message"]["content"]
            if adviser_output
            else "Adviser not available."
        )

        print("\nADVISER:")
        print(advice)
