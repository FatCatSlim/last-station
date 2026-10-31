import os
import subprocess  # Run external commands, e.g., clearing the screen
import textwrap  # Format text output, e.g., wrapping long messages

from agent_runner import build_adviser_input, run_adviser
from cache import (
    add_cycle_report,
    get_recent_cycle_history,
    load_resources,
    save_resources,
)
from config import STATION_NAME
from tools import (
    advance_cycle,
    check_hub_health,
    dispatch_expedition,
    get_engineering,
    get_expedition,
    get_hub_info,
    get_infrastructure,
    get_resources,
    request_generator_repair,
)

# Power Thresholds
MAINTENANCE_POWER_THRESHOLD = 60  # level at which maintenance is required
DEGRADED_POWER_THRESHOLD = 50  # level at which power is considered degraded
CRITICAL_POWER_THRESHOLD = 20  # level at which power is critical
STANDBY_POWER_THRESHOLD = 10  # level at which standby mode is activated


def get_station_mode(hub_status):
    if hub_status["status"] == "online":
        return "CONNECTED"
    else:
        return "SURVIVAL"


def get_resource_warning(resources):
    warnings = []
    power = resources.get("power")
    if power <= MAINTENANCE_POWER_THRESHOLD:
        warnings.append("Service/maintenance required.")
    if power <= DEGRADED_POWER_THRESHOLD:
        warnings.append("Degraded power warning. Production reduced by 20%.")
    if power <= CRITICAL_POWER_THRESHOLD:
        warnings.append("Critical power warning.")
    if power <= STANDBY_POWER_THRESHOLD:
        warnings.append("Power low. STANDBY mode activated.")
    if power == 0:
        warnings.append("Total power loss!")
    return warnings


def get_station_condition(warnings):
    warning_count = len(warnings)
    if warning_count == 0:
        return "STABLE"
    elif warning_count <= 2:
        return "STRAINED"
    else:
        return "CRITICAL"


def get_station_message(station_condition):
    if station_condition == "STABLE":
        return "No active station warnings."
    elif station_condition == "STRAINED":
        return "Operator attention recommended."
    else:
        return "Immediate operator attention required!"


def resource_bar(value):  # Returns a visual representation of resources
    filled = int((value / 100) * 10)
    empty = 10 - filled
    return "[" + "#" * filled + "-" * empty + "]"


# UI part ____________________
def print_simulation_status(
    hub_status,
    station_mode,
    hub_info,
    resources,
    infrastructure,
    show_operator=True,
    show_operator_interface=True,
    auto_mode=False,
    auto_cycle_mode=None,
):
    if hub_status["status"] == "online":
        warnings = get_resource_warning(resources)
        station_condition = get_station_condition(warnings)
        station_message = get_station_message(station_condition)
        title = (
            f"====== {hub_info['hub_name']} {hub_info['hub_version']} "
            f"// Operation Terminal ======"
        )
        hub_line = (
            f"Hub: {hub_status['status'].upper()}  |  "
            f"Cycle: {resources['cycle']}  |  Mode: {station_mode}"
        )
        condition_line = (
            f"Station Condition: {station_condition} (Alerts: {len(warnings)})"
        )
        resource_title = " RESOURCES MONITOR "
        foodwater_line = (
            f"Food:  {resource_bar(resources['food'])}"
            f" {resources['food']:>5.1f} / 100 | "
            f"Water: {resource_bar(resources['water'])}"
            f" {resources['water']:>5.1f} / 100 "
        )
        powerscrap_line = (
            f"Power: {resource_bar(resources['power'])}"
            f" {resources['power']:>5.1f} / 100 | "
            f"Scrap: {resources['scrap']}"
        )
        infrastructure_title = " INFRASTRUCTURE STATUS "
        power_status = (
            "ONLINE" if infrastructure["power_system"]["operational"] else "OFFLINE"
        )
        power_line = (
            f"Power: {power_status:<7}  |  "
            f"Generator: {infrastructure['power_system']['wind_generators'].upper()} --> "
            f"Output: {infrastructure['power_system']['output']}%"
        )
        water_status = (
            "ONLINE" if infrastructure["water_system"]["operational"] else "OFFLINE"
        )
        water_line = (
            f"Water: {water_status:<7}  |  "
            f"Source: {infrastructure['water_system']['source'].upper()}  |  "
            f"Pump: {infrastructure['water_system']['pump'].upper()}"
        )
        farm_status = "ONLINE" if infrastructure["farm"]["operational"] else "OFFLINE"
        farm_line = (
            f"Farm:  {farm_status:<7}  |  "
            f"Light: {infrastructure['farm']['lights'].upper()}"
        )
        warnings_title = " WARNINGS "
        operator_title = " OPERATOR INTERFACE "
        menu_line1 = f"{'[1] Advance Normal Cycle':<25}  [2] Advance Ration Cycle"
        menu_line2 = f"{'[E] Expedition':<25}  [R] Engineering / Repair"
        menu_line3 = f"{'[M] Sector Map':<25}  [L] Recent Cycle Log"
        menu_line4 = f"{'[A] Ask Adviser':<25}  [Q] Quit"
        menu_line5 = f"{'[T] Toggle Auto Mode':<25}"
        if auto_mode:
            cycle_type = auto_cycle_mode.upper() if auto_cycle_mode else "N/A"
            auto_mode_line = f"Auto Mode: ON | Type: {cycle_type}"
        else:
            auto_mode_line = f"Auto Mode: OFF | Manual Control"

        print("╔" + "═" * 68 + "╗")
        print("║" + f"{title.center(68)}" + "║")
        print("╠" + "═" * 68 + "╣")
        print("║" + " " * 68 + "║")
        print("║" + f" {hub_line.ljust(67)}" + "║")
        print("║" + f" {condition_line.ljust(67)}" + "║")
        print("║" + f" {station_message.ljust(67)}" + "║")
        print("║" + " " * 68 + "║")
        print("╠" + resource_title.center(68, "═") + "╣")
        print("║" + " " * 68 + "║")
        print("║" + f" {foodwater_line.ljust(67)}" + "║")
        print("║" + f" {powerscrap_line.ljust(67)}" + "║")
        print("║" + " " * 68 + "║")
        print("╠" + infrastructure_title.center(68, "═") + "╣")
        print("║" + " " * 68 + "║")
        print("║" + f" {power_line.ljust(67)}" + "║")
        print("║" + f" {water_line.ljust(67)}" + "║")
        print("║" + f" {farm_line.ljust(67)}" + "║")
        print("║" + " " * 68 + "║")
        print("╠" + warnings_title.center(68, "═") + "╣")
        print("║" + " " * 68 + "║")
        if warnings:
            for warning in warnings:
                warning_line = f"[!] {warning}"
                print("║" + f" {warning_line.ljust(67)}" + "║")
        else:
            warning_line = "[CLEAR] No warnings"
            print("║" + f" {warning_line.ljust(67)}" + "║")
        print("║" + " " * 68 + "║")
        if show_operator:
            print("╠" + operator_title.center(68, "═") + "╣")
            print("║" + " " * 68 + "║")
            print("║" + f" {auto_mode_line.center(67)}" + "║")
            print("║" + " " * 68 + "║")
            print("║" + f" {menu_line1.ljust(67)}" + "║")
            print("║" + f" {menu_line2.ljust(67)}" + "║")
            print("║" + f" {menu_line3.ljust(67)}" + "║")
            print("║" + f" {menu_line4.ljust(67)}" + "║")
            print("║" + f" {menu_line5.ljust(67)}" + "║")
            print("║" + " " * 68 + "║")
            print("╚" + "═" * 68 + "╝")

    else:  # IF hub is offline
        print("Hub: OFFLINE")
        print(f"Station Mode: {station_mode}")
        print(f"Last Known Cycle: {resources['cycle']}")
        print("LAST KNOWN RESOURCES:")
        for resource, amount in resources.items():
            if resource != "cycle":
                print(f"  {resource.capitalize()}: {amount}")
        warnings = get_resource_warning(resources)
        if warnings:
            print("\nWARNING:")
            for warning in warnings:
                print(f"  {warning}")
        print(
            f"Entering survival mode."
            f"\n[ Survival Mode is currently in development ]"
        )


def print_sector_map():
    print(f"""
            ╔═══════════════ RAVEN LINE // SECTOR MAP ═══════════════╗
            ║                                                        ║
            ║                      [ NORTH LIFT ]                    ║
            ║                      Surface Access                    ║
            ║                            ?                           ║
            ║                            ║                           ║
            ║   [ DEPOT-14 ]═══════[ {STATION_NAME:^8} ]═══════[ RELAY-9 ]    ║
            ║    Scrap Yard        HOME STATION          Power       ║
            ║         +                  @                 !         ║
            ║         ║                  ║                           ║
            ║   [ BLACK TUNNEL ]═════[ GARDEN-7 ]═════[ SUMP-6 ]     ║
            ║     Sealed Route        Food Sector       Water        ║
            ║         !                  +                +          ║
            ║                                                        ║
            ║   @ Home   + Available   ! Danger   ? Unknown          ║
            ╚════════════════════════════════════════════════════════╝
          """)
    input("Press Enter to return to the main menu...")


def clear_screen():
    if os.name == "nt":
        subprocess.run("cls", check=False, shell=True)


def run_simulation():  # simulation start
    resources = {
        "cycle": None,
        "food": None,
        "water": None,
        "power": None,
        "scrap": None,
    }
    hub_status = check_hub_health()
    station_mode = get_station_mode(hub_status)
    hub_info = {"hub_name": None, "hub_version": None}
    if hub_status["status"] == "online":
        hub_info = get_hub_info()
        updated_resources = get_resources()
        if updated_resources is not None:
            resources = updated_resources
            save_resources(resources)
        else:
            hub_status["status"] = "offline"
            station_mode = get_station_mode(hub_status)
            cached_resources = load_resources()
            if cached_resources:
                resources = cached_resources
    else:
        cached_resources = load_resources()
        if cached_resources:
            resources = cached_resources

    # MAIN BLOCK
    auto_mode = False
    auto_cycle_mode = None
    show_operator_interface = True
    if hub_status["status"] == "online":
        while True:
            clear_screen()
            infrastructure = get_infrastructure()
            print_simulation_status(
                hub_status,
                station_mode,
                hub_info,
                resources,
                infrastructure,
                show_operator_interface=show_operator_interface,
                auto_mode=auto_mode,
                auto_cycle_mode=auto_cycle_mode,
            )
            choice = input("Select an option: ").strip().lower()
            if auto_mode and choice in ("1", "2"):
                print("Manual mode is disabled while Auto Mode is active.")
                input("\nPress Enter to return...")
                continue
            full_cycle_data = None
            cycle_selection = None

            if choice == "1":
                cycle_selection = "normal"
            elif choice == "2":
                cycle_selection = "ration"
            elif choice == "e":
                clear_screen()
                expedition_data = get_expedition()
                if expedition_data is None:
                    print("Failed to retrieve expedition status.")
                    input("\nPress Enter to return...")
                    continue
                elif expedition_data["status"] == "idle":
                    expedition_title = "Expedition Control"
                    status_line = f"Status: {expedition_data['status'].upper()}"
                    control_title = " Dispatch Control "
                    location_title = " Available Locations for Dispatch: "
                    location_1 = "  [1]. Garden-7 (Food Sector)"
                    location_2 = "  [2]. Sump-6 (Water Sector)"
                    location_3 = "  [3]. Depot-14 (Scrap Yard)"

                    print("╔" + "═" * 68 + "╗")
                    print("║" + f" {expedition_title.center(66)} " + "║")
                    print("╠" + "═" * 68 + "╣")
                    print("║" + " " * 68 + "║")
                    print("║" + f" {status_line.ljust(66)} " + "║")
                    print("║" + " " * 68 + "║")
                    print("╠" + control_title.center(68, "═") + "╣")
                    print("║" + " " * 68 + "║")
                    print(
                        "║"
                        + location_title.ljust(
                            68,
                        )
                        + "║"
                    )
                    print("║" + " " * 68 + "║")
                    print("║" + f" {location_1}".ljust(68) + "║")
                    print("║" + f" {location_2}".ljust(68) + "║")
                    print("║" + f" {location_3}".ljust(68) + "║")
                    print("║" + " " * 68 + "║")
                    print("╚" + "═" * 68 + "╝")

                    dispatch_choice = (
                        input("Select a location to dispatch (1-3) or [B] Go back: ")
                        .strip()
                        .lower()
                    )
                    if dispatch_choice == "1":
                        dispatch_location = "garden_7"
                    elif dispatch_choice == "2":
                        dispatch_location = "sump_6"
                    elif dispatch_choice == "3":
                        dispatch_location = "depot_14"
                    elif dispatch_choice == "b":
                        continue
                    else:
                        print("Invalid option. Please try again.")
                        input("\nPress Enter to return...")
                        continue
                    expedition_response = dispatch_expedition(dispatch_location)
                    if expedition_response:
                        print(
                            f"Expedition dispatched to {expedition_response['location']}. "
                            f"Cycle remaining: {expedition_response['cycle_remaining']}."
                        )
                    else:
                        print("Failed to dispatch expedition. Hub connection lost.")
                else:
                    expedition_title = "Expedition Control"
                    status_line = f"Status: {expedition_data['status'].upper()}"
                    location_line = f"Current Location: {expedition_data['location']}"
                    cycles_line = (
                        f"Cycles Remaining: {expedition_data['cycle_remaining']}"
                    )

                    print("╔" + "═" * 68 + "╗")
                    print("║" + f" {expedition_title.center(66)} " + "║")
                    print("╠" + "═" * 68 + "╣")
                    print("║" + " " * 68 + "║")
                    print("║" + f" {status_line.ljust(66)} " + "║")
                    print("║" + f" {location_line.ljust(66)} " + "║")
                    print("║" + f" {cycles_line.ljust(66)} " + "║")
                    print("║" + " " * 68 + "║")
                    print("╚" + "═" * 68 + "╝")
                input("\nPress Enter to return...")
                continue

            # Repair/Engineering Section
            elif choice == "r":  # get_engineering, request_generator_repair
                while True:
                    clear_screen()
                    engineering = get_engineering()

                    if engineering is None:
                        print("Could not retrieve engineering status.")
                        input("\nPress Enter to return...")
                        break

                    # Set screen text based on current engineering state.
                    if engineering["status"] == "available":
                        repair_prompt = "Engineering team available."
                        repair_menu = (
                            f"{'[Y] Request Generator Repair':<25}  [N] Return"
                        )
                    else:
                        repair_prompt = "Engineering team busy with repairs."
                        repair_menu = "[ENTER] Return"

                    engineering_title = " Engineering / Repair "

                    engineering_line1 = (
                        f"{'Status: ' + engineering['status'].upper():<20}" + "  |  "
                        f"Cycle Remaining: {engineering['cycle_remaining']}"
                    )

                    engineering_line2 = (
                        f"{'Repair Target: ' + str(engineering['repair_target']):<20}"
                        + "  |  "
                        f"Scrap: {engineering['scrap']}"
                    )

                    repair_title = " Repair Control "

                    print("╔" + "═" * 68 + "╗")
                    print("║" + engineering_title.center(68, " ") + "║")
                    print("╠" + "═" * 68 + "╣")
                    print("║" + " " * 68 + "║")
                    print("║" + f" {engineering_line1.ljust(66)} " + "║")
                    print("║" + f" {engineering_line2.ljust(66)} " + "║")
                    print("║" + " " * 68 + "║")
                    print("╠" + repair_title.center(68, "═") + "╣")
                    print("║" + " " * 68 + "║")
                    print("║" + f" {repair_prompt.center(66)} " + "║")
                    print("║" + " " * 68 + "║")
                    print("║" + f" {repair_menu.ljust(66)} " + "║")
                    print("╚" + "═" * 68 + "╝")

                    if engineering["status"] == "available":
                        repair_choice = input("Select an option: ").strip().lower()

                        if repair_choice == "y":
                            repair_response = request_generator_repair()

                            if repair_response is None:
                                print("Failed to request generator repair.")
                                input("\nPress Enter to return...")
                                break

                            # Refresh resources
                            updated_resources = get_resources()

                            if updated_resources is not None:
                                resources = updated_resources
                            # screen redraws with the updated resources.
                            continue

                        elif repair_choice == "n":
                            break

                        else:
                            print("Invalid option, please select 'y' or 'n'.")
                            input("\nPress Enter to try again...")

                    else:
                        input("\nPress Enter to return...")
                        break

                continue

            # Sector map
            elif choice == "m":
                clear_screen()
                print_sector_map()
                continue

            # Recent cycle log
            elif choice == "l":
                clear_screen()
                log_title = " Recent Cycle Log "
                print("─" * 68)
                print(log_title.center(68))
                print("─" * 68)

                recent_history = get_recent_cycle_history()
                if recent_history:
                    for cycle_report in recent_history:
                        cycle_resources = cycle_report["resources"]
                        consumption = cycle_report["consumption"]
                        cycle_number = cycle_resources["cycle"]
                        action = cycle_report["action"]
                        expedition_reward = cycle_report.get("expedition_reward", {})
                        supply = cycle_report.get("supply", {})

                        cycle_line = f"Cycle {cycle_number} | {action.upper()}"
                        resources_line = (
                            f"Food: {cycle_resources['food']} | "
                            f"Water: {cycle_resources['water']} | "
                            f"Power: {cycle_resources['power']} | "
                            f"Scrap: {cycle_resources['scrap']}"
                        )

                        consumption_part = []
                        for r, a in consumption.items():
                            if a > 0:
                                consumption_part.append(f"{r.capitalize()} -{a}")
                        flow_line = "Consumed: " + " / ".join(consumption_part)

                        if sum(supply.values()) > 0:
                            supply_part = []
                            for r, a in supply.items():
                                if a > 0:
                                    supply_part.append(f"{r.capitalize()} +{a}")
                            flow_line += " | Supply: " + " / ".join(supply_part)
                        print(f"\n{cycle_line}")
                        print(resources_line)
                        print(flow_line)

                        if sum(expedition_reward.values()) > 0:
                            reward_part = []
                            for r, a in expedition_reward.items():
                                if a > 0:
                                    reward_part.append(f"{r.capitalize()} +{a}")
                            print("Expedition Reward: " + " / ".join(reward_part))
                        print("-" * 68)
                    input("\nPress Enter to return...")
                else:
                    print("No recent cycle history available.")
                    input("\nPress Enter to return...")
                continue

            elif choice == "a":
                clear_screen()
                print_simulation_status(
                    hub_status,
                    station_mode,
                    hub_info,
                    resources,
                    infrastructure,
                    show_operator=False,
                    show_operator_interface=show_operator_interface,
                    auto_mode=auto_mode,
                    auto_cycle_mode=auto_cycle_mode,
                )
                adviser_input = build_adviser_input()
                if adviser_input is None:
                    input_text = "Adviser not available (cycle history is empty)"
                    print("\n" + " ..." + input_text.ljust(65) + " ")
                    input("\nPress Enter to return...")
                else:
                    adviser_title = " Adviser Console "
                    print("╠" + "═" * 68 + "╣")
                    print("║" + adviser_title.center(68) + "║")
                    print("╠" + "─" * 68 + "╣")
                    print("║" + " Adviser Response: ".ljust(68) + "║")
                    adviser_response = run_adviser(adviser_input)
                    adviser_text = adviser_response["message"]["content"]
                    wrapped_text = textwrap.wrap(adviser_text, width=66)

                    for line in wrapped_text:
                        print("║" + f" {line.ljust(66)} " + "║")
                    print("╚" + "─" * 68 + "╝")

                    input("\nPress Enter to return...")
                continue
            elif choice == "t":
                if auto_mode:
                    auto_mode = False
                    auto_cycle_mode = None
                else:
                    while True:
                        selection = (
                            input(
                                "Select auto cycle mode (1: Normal / 2: Ration / B: Back): "
                            )
                            .strip()
                            .lower()
                        )
                        if selection == "1":
                            auto_cycle_mode = "normal"
                            auto_mode = True
                            break
                        elif selection == "2":
                            auto_cycle_mode = "ration"
                            auto_mode = True
                            break
                        elif selection == "b":
                            auto_mode = False
                            auto_cycle_mode = None
                            break
                        else:
                            clear_screen()
                            print_simulation_status(
                                hub_status,
                                station_mode,
                                hub_info,
                                resources,
                                infrastructure,
                                show_operator_interface=show_operator_interface,
                                auto_mode=auto_mode,
                                auto_cycle_mode=auto_cycle_mode,
                            )

                            print("Invalid selection. Please try again.")
                continue
            elif choice == "q":
                print("Session ended.")
                break
            else:
                print("Invalid option. Please try again.")
                input("\nPress Enter to return...")
                continue

            if cycle_selection is not None:
                full_cycle_data = advance_cycle(cycle_selection)

            if full_cycle_data:
                resources = full_cycle_data["resources"]
                power_degradation = full_cycle_data["power_degradation"]
                clear_screen()

                cycles_title = " Cycle Report "
                operation_line = full_cycle_data["action"].upper()
                consumption_line = " | ".join(
                    f"{resource.capitalize()}: -{amount:g}"
                    for resource, amount in full_cycle_data["consumption"].items()
                    if amount > 0
                )
                supply_line = " | ".join(
                    f"{resource.capitalize()}: +{amount:g}"
                    for resource, amount in full_cycle_data["supply"].items()
                    if amount > 0
                )
                power_line = (
                    f"Power Degradation: -{power_degradation:g}"
                    if power_degradation > 0
                    else ""
                )
                rewards_line = " | ".join(
                    f"{resource.capitalize()}: +{amount:g}"
                    for resource, amount in full_cycle_data["expedition_reward"].items()
                    if amount > 0
                )

                print("╔" + "═" * 68 + "╗")
                print("║" + cycles_title.center(68) + "║")
                print("╠" + "═" * 68 + "╣")
                print("║" + f" Operation: {operation_line}".ljust(68) + "║")
                if consumption_line:
                    print("║" + f" Consumed: {consumption_line}".ljust(68) + "║")
                if supply_line:
                    print("║" + f" Supplied: {supply_line}".ljust(68) + "║")
                if power_line:
                    print("║" + f" {power_line}".ljust(68) + "║")
                if rewards_line:
                    print("║" + f" Expedition Rewards: {rewards_line}".ljust(68) + "║")
                print("╚" + "═" * 68 + "╝")

                expedition_data = get_expedition()
                direction = "at"

                if expedition_data is not None:
                    if expedition_data["status"] == "outbound":
                        direction = "to"
                    elif expedition_data["status"] == "returning":
                        direction = "from"

                    if expedition_data["status"] != "idle":
                        print(
                            f"Expedition Status: {expedition_data['status'].upper()} "
                            f"{direction} {expedition_data['location']}. "
                            f"Cycle Remaining: {expedition_data['cycle_remaining']}."
                        )

                # Save warnings and station condition to the full cycle data
                warnings = get_resource_warning(resources)
                station_condition = get_station_condition(warnings)
                full_cycle_data["warnings"] = warnings
                full_cycle_data["station_condition"] = station_condition

                save_resources(resources)
                add_cycle_report(full_cycle_data)

                print("\nCycle advanced.")
                input("\nPress Enter to return...")
            else:
                print("Hub connection lost. Cycle not advanced.")
                hub_status["status"] = "offline"
                station_mode = get_station_mode(hub_status)
                print_simulation_status(
                    hub_status,
                    station_mode,
                    hub_info,
                    resources,
                    infrastructure,
                    show_operator_interface=show_operator_interface,
                    auto_mode=auto_mode,
                    auto_cycle_mode=auto_cycle_mode,
                )
                break
    else:
        # If the hub is offline
        clear_screen()
        print_simulation_status(
            hub_status,
            station_mode,
            hub_info,
            resources,
            infrastructure=None,
            show_operator_interface=show_operator_interface,
            auto_mode=auto_mode,
            auto_cycle_mode=auto_cycle_mode,
        )
        input("\nPress Enter to return...")


if __name__ == "__main__":
    run_simulation()
