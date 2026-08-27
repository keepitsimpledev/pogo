import csv
import json


def load():
    with open("pokemon-in-go.json", "r") as file:
        loaded_json_data = json.load(file)
    return loaded_json_data


# TODO: make it so we don't have to put [13:] all over the place

UNRELEASED = ["Phione", "Wishiwashi", "Pyukumuku", "Silvally", "Minior", "Magearna", "Chewtle", "Drednaw", "Milcery",
              "Alcremie", "Pincurchin", "Eiscue", "Cufant", "Copperajah", "Dracozolt", "Arctozolt", "Dracovish",
              "Arctovish", "Glastrier", "Spectrier", "Calyrex", "Basculegion", "Maschiff", "Mabosstiff", "Bramblin",
              "Brambleghast", "Capsakid", "Scovillain", "Rellor", "Rabsca", "Finizen", "Palafin", "Cyclizar", "Veluza",
              "Farigiraf", "GreatTusk", "ScreamTail", "BruteBonnet", "FlutterMane", "SlitherWing", "SandyShocks",
              "IronTreads", "IronBundle", "IronHands", "IronJugulis", "IronMoth", "IronThorns", "WoChien", "ChienPao",
              "TingLu", "ChiYu", "RoaringMoon", "IronValiant", "Koraidon", "Miraidon", "WalkingWake", "IronLeaves",
              "Okidogi", "Munkidori", "Fezandipiti", "Ogerpon", "Archaludon", "GougingFire", "RagingBolt",
              "IronBoulder", "IronCrown", "Terapagos", "Pecharunt"]


def filter_data(raw_data_json):
    data_out = {}
    for pokemon in raw_data_json:
        name = pokemon["id"]
        if name.lower() in map(str.lower, UNRELEASED):
            print("skipping {} - unreleased".format(name))
        else:
            data_out[name] = parse_single_pokemon(pokemon)

        for form in pokemon["regionForms"]:
            if name.lower() in map(str.lower, UNRELEASED) or "MINIOR" in name:
                print("skipping {} - unreleased".format(name))
            else:
                data_out[form] = parse_single_pokemon(pokemon["regionForms"][form])

    return data_out


def parse_single_pokemon(pokemon):
    parsed = {}
    parsed["bulk"] = pokemon["stats"]["defense"] + pokemon["stats"]["stamina"]

    parsed["type"] = pokemon["primaryType"]["type"]
    if pokemon["secondaryType"] is not None:
        parsed["type2"] = pokemon["secondaryType"]["type"]

    parsed["fast"] = []
    for attack_name in pokemon["quickMoves"]:
        attack = pokemon["quickMoves"][attack_name]
        speed = float(attack["combat"]["energy"]) / float(attack["combat"]["turns"])
        speed = round(speed, 2)
        damage_per_turn = float(attack["combat"]["power"]) / float(attack["combat"]["turns"])
        damage_per_turn = round(damage_per_turn, 2)
        if speed >= 4:
            parsed["fast"].append({"type": attack["type"]["type"], "speed": speed, "power": damage_per_turn})

    parsed["charged"] = []
    for attack_name in pokemon["cinematicMoves"]:
        attack = pokemon["cinematicMoves"][attack_name]
        cost = abs(int(attack["combat"]["energy"]))
        power = abs(int(attack["combat"]["power"]))
        if cost <= 45:
            parsed["charged"].append({"type": attack["type"]["type"], "cost": cost, "power": power})

    return parsed


def get_typechart(file_name):
    typechart = {}
    with open(file_name, "r", newline="\n") as raw_typechart:
        reader = csv.DictReader(raw_typechart)
        for row in reader:
            types = {}
            for resistance in row:
                if resistance == "TYPE":
                    continue
                elif row[resistance] == "":
                    continue
                else:
                    types[resistance] = int(row[resistance])
            typechart[row["TYPE"]] = types
    return typechart


def calculate_resistances(all_pokemon):
    typechart = get_typechart("resistance typechart.csv")

    for pokemon_name in all_pokemon:
        pokemon = all_pokemon[pokemon_name]
        pokemon["resistances"] = {}

        primary_resistances = typechart[pokemon["type"][13:]]
        secondary_resistances = None if "type2" not in pokemon else typechart[pokemon["type2"][13:]]

        for resistance in primary_resistances:
            if resistance not in pokemon["resistances"]:
                pokemon["resistances"][resistance] = primary_resistances[resistance]
            else:
                pokemon["resistances"][resistance] += primary_resistances[resistance]

        if secondary_resistances is None:
            continue

        for resistance in secondary_resistances:
            if resistance not in pokemon["resistances"]:
                pokemon["resistances"][resistance] = secondary_resistances[resistance]
            else:
                pokemon["resistances"][resistance] += secondary_resistances[resistance]


def find_counters(all_pokemon):
    resistant_pokemon = []
    typechart = get_typechart("damage typechart.csv")

    for pokemon_name in all_pokemon:
        current_pokemon = all_pokemon[pokemon_name]
        for resistance in current_pokemon["resistances"]:
            counter_types = []
            for attack_type in typechart:
                if resistance in typechart[attack_type] and typechart[attack_type][resistance] == 1:
                    counter_types.append(attack_type)

            fast_counters = set()
            for fast_attack in current_pokemon["fast"]:
                if fast_attack["type"][13:] in counter_types:
                    fast_counters.add(fast_attack["type"][13:])

            charged_counters = set()
            fastest = 99.9

            for charged_attack in current_pokemon["charged"]:
                cost = abs(int(charged_attack["cost"]))
                charged_ratio = float(charged_attack["power"]) / cost
                if charged_attack["type"][13:] in counter_types:
                    charged_counters.add(charged_attack["type"][13:])

                    for fast_attack in current_pokemon["fast"]:
                        attack_speed = float(cost/fast_attack["speed"])
                        attack_speed = round(attack_speed, 2)
                        is_dual_counter = fast_attack["type"][13:] in counter_types
                        is_very_fast = attack_speed < 8.1 and charged_ratio >= 1
                        has_strong_charged = charged_ratio >= 1.25
                        has_strong_fast = fast_attack["power"] >= 3.5 and fast_attack["type"][13:] in counter_types

                        if attack_speed < fastest and attack_speed <= 10\
                                and (is_dual_counter or is_very_fast or has_strong_fast or has_strong_charged):
                            fastest = attack_speed

            if len(current_pokemon["fast"]) == 0 or len(charged_counters) == 0:
                continue

            modifier = current_pokemon["resistances"][resistance]
            if modifier < 0 and fastest < 99.9:
                formatted_fast = current_pokemon["fast"]
                fast_len = len(str(formatted_fast)) - 1
                formatted_fast = str(formatted_fast)[1:fast_len].replace("'", "").replace("type: ", "")

                formatted_charged = current_pokemon["charged"]
                charged_len = len(str(formatted_charged)) - 1
                formatted_charged = str(formatted_charged)[1:charged_len].replace("'", "").replace("type: ", "")

                resistant_pokemon.append([pokemon_name,
                                          resistance,
                                          modifier,
                                          current_pokemon["bulk"],
                                          fastest,
                                          fast_counters if len(fast_counters) > 0 else [],
                                          charged_counters if len(charged_counters) > 0 else [],
                                          formatted_fast,
                                          formatted_charged])

    return sorted(resistant_pokemon, key=lambda x: (x[1], x[2], -x[3]))


def find_attackers(all_pokemon):
    attackers = []
    for pokemon_name in all_pokemon:
        current_pokemon = all_pokemon[pokemon_name]
        has_2nd_type = "type2" in current_pokemon

        for charged_attack in current_pokemon["charged"]:
            power = float(charged_attack["power"] / charged_attack["cost"])
            has_good_power_ratio = power >= 1.25
            charged_is_type1 = charged_attack["type"] == current_pokemon["type"]
            charged_is_type2 = has_2nd_type and charged_attack["type"] == current_pokemon["type"]
            for fast_attack in current_pokemon["fast"]:
                speed = float(charged_attack["cost"] / fast_attack["speed"])
                speed = round(speed, 2)
                fast_is_type1 = fast_attack["type"] == current_pokemon["type"]
                fast_is_type2 = has_2nd_type and fast_attack["type"] == current_pokemon["type2"]
                fast_attack_is_strong = fast_attack["power"] >= 3.5
                if has_good_power_ratio or fast_attack_is_strong:
                    stab1 = (charged_is_type1 and has_good_power_ratio) or (fast_is_type1 and fast_attack_is_strong)
                    stab2 = (charged_is_type2 and has_good_power_ratio) or (fast_is_type2 and fast_attack_is_strong)
                    stab = charged_attack["type"] if stab1 or stab2 else "none"
                    attackers.append([pokemon_name,
                                      charged_attack["type"],
                                      current_pokemon["bulk"],
                                      speed,
                                      stab,
                                      fast_attack["type"],
                                      charged_attack["type"]])

    return sorted(attackers, key=lambda x: (x[1], x[4], -x[2], x[3]))


def find_singletype_attackers(all_pokemon):
    singletype_pokemon = []
    for pokemon_name in all_pokemon:
        current_pokemon = all_pokemon[pokemon_name]
        if "type2" in current_pokemon:
            continue

        fastest_attack = 0
        for fast_attack in current_pokemon["fast"]:
            if fast_attack["type"] == current_pokemon["type"] and fast_attack["speed"] > fastest_attack:
                fastest_attack = fast_attack["speed"]

        cheapest_charge = 999
        for charged_attack in current_pokemon["charged"]:
            if charged_attack["type"] == current_pokemon["type"] and charged_attack["cost"] < cheapest_charge:
                cheapest_charge = charged_attack["cost"]

        if fastest_attack > 0 and cheapest_charge < 999:
            singletype_pokemon.append([pokemon_name,
                                       current_pokemon["type"],
                                       float(cheapest_charge / fastest_attack),
                                       current_pokemon["bulk"]])

    return sorted(singletype_pokemon, key=lambda x: (x[1], x[2], -x[3]))


def find_singleattacktype_attackers(all_pokemon):
    singleattacktype = []
    for pokemon_name in all_pokemon:
        current_pokemon = all_pokemon[pokemon_name]

        fastest_type1_attack = 0
        fastest_type2_attack = 0
        for fast_attack in current_pokemon["fast"]:
            if fast_attack["type"] == current_pokemon["type"] and fast_attack["speed"] > fastest_type1_attack:
                fastest_type1_attack = fast_attack["speed"]
            if "type2" in current_pokemon and fast_attack["type"] == current_pokemon["type2"] and fast_attack["speed"] > fastest_type2_attack:
                fastest_type2_attack = fast_attack["speed"]

        cheapest_type1_charge = 999
        cheapest_type2_charge = 999
        for charged_attack in current_pokemon["charged"]:
            if charged_attack["type"] == current_pokemon["type"] and charged_attack["cost"] < cheapest_type1_charge:
                cheapest_type1_charge = charged_attack["cost"]
        for charged_attack in current_pokemon["charged"]:
            if "type2" in current_pokemon and charged_attack["type"] == current_pokemon["type2"] and charged_attack["cost"] < cheapest_type2_charge:
                cheapest_type2_charge = charged_attack["cost"]
        if fastest_type1_attack > 0 and cheapest_type1_charge < 999:
            speed = float(cheapest_type1_charge / fastest_type1_attack)
            singleattacktype.append([current_pokemon["type"], pokemon_name, speed, current_pokemon["bulk"]])
        if fastest_type2_attack > 0 and cheapest_type2_charge < 999:
            speed = float(cheapest_type2_charge / fastest_type2_attack)
            singleattacktype.append([current_pokemon["type2"], pokemon_name, speed, current_pokemon["bulk"]])

    return sorted(singleattacktype, key=lambda x: (x[0], x[2], -x[3]))


def save(pokemon, headers, filename):
    with open(filename, "w", newline="\n",) as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for p in pokemon:
            writer.writerow(p)


if __name__ == '__main__':
    raw_data = load()
    pokemon_data = filter_data(raw_data)
    calculate_resistances(pokemon_data)

    counters = find_counters(pokemon_data)
    counters_headers = ["pokemon", "resists", "modifier", "bulk", "fastest", "fast counters", "charged counters", "fast attacks", "charged attacks"]
    save(counters, counters_headers, "rocket counters.csv")

    attackers = find_attackers(pokemon_data)
    attackers_headers = ["pokemon", "type", "bulk", "speed", "stab", "fast", "charged"]
    save(attackers, attackers_headers, "rocket attackers.csv")

    singletype_pokemon = find_singletype_attackers(pokemon_data)
    singletype_headers = ["pokemon", "type", "attack speed", "bulk"]
    save(singletype_pokemon, singletype_headers, "single-type pokemon.csv")

    singleattacktype_pokemon = find_singleattacktype_attackers(pokemon_data)
    singleattack_headers = ["type", "pokemon", "speed", "bulk"]
    save(singleattacktype_pokemon, singleattack_headers, "single-attack-type pokemon.csv")
