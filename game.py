import random
from llm_controller import TEAM_MODELS

class Location:
    def __init__(self, name, connections, resources):
        self.name = name
        self.connections = connections
        self.resources = resources
        self.control = None
        self.units = {}  # team_name: list[Unit]

class Unit:
    def __init__(self, id, type, health, strength):
        self.id = id
        self.type = type
        self.health = health
        self.strength = strength

class Team:
    def __init__(self, name):
        self.name = name
        self.units = []
        self.resources = 0
        self.controlled_locations = []

class Game:
    def __init__(self):
        self.turn = 0
        self.locations = []
        names = ['Bel Air', 'Aberdeen Proving Ground', 'Havre de Grace', 'Edgewood', 'Joppatowne', 'Fallston']
        conn_dict = {
            'Bel Air': ['Fallston', 'Joppatowne', 'Edgewood', 'Aberdeen Proving Ground'],
            'Aberdeen Proving Ground': ['Edgewood', 'Havre de Grace', 'Bel Air'],
            'Havre de Grace': ['Aberdeen Proving Ground'],
            'Edgewood': ['Aberdeen Proving Ground', 'Joppatowne', 'Bel Air'],
            'Joppatowne': ['Edgewood', 'Bel Air'],
            'Fallston': ['Bel Air']
        }
        for n in names:
            loc = Location(n, conn_dict.get(n, []), 1)
            self.locations.append(loc)

        self.teams = {
            'Blue': Team('Blue'),
            'Red': Team('Red')
        }

        # Initial setup
        bel_air = self.get_location_by_name('Bel Air')
        aberdeen = self.get_location_by_name('Aberdeen Proving Ground')
        bel_air.control = 'Blue'
        aberdeen.control = 'Red'
        self.teams['Blue'].controlled_locations.append('Bel Air')
        self.teams['Red'].controlled_locations.append('Aberdeen Proving Ground')

        bel_air.units['Blue'] = []
        for i in range(1, 6):
            u = Unit(f'Blue-{i}', 'infantry', 3, 1)
            self.teams['Blue'].units.append(u)
            bel_air.units['Blue'].append(u)

        aberdeen.units['Red'] = []
        for i in range(1, 6):
            u = Unit(f'Red-{i}', 'infantry', 3, 1)
            self.teams['Red'].units.append(u)
            aberdeen.units['Red'].append(u)

    def get_location_by_name(self, name):
        for loc in self.locations:
            if loc.name == name:
                return loc
        return None

    def get_unit_by_id(self, uid):
        for team in self.teams.values():
            for u in team.units:
                if u.id == uid:
                    return u
        return None

    def get_location_of_unit(self, uid):
        for loc in self.locations:
            for team_name, us in loc.units.items():
                for u in us:
                    if u.id == uid:
                        return loc
        return None

    def get_visible_state(self, team_name):
        team = self.teams[team_name]
        opponent_name = 'Red' if team_name == 'Blue' else 'Blue'
        state = {
            'team': team_name,
            'resources': team.resources,
            'controlled_locations': team.controlled_locations,
            'own_unit_count': len(team.units),
            'opponent_unit_count': len(self.teams[opponent_name].units),
            'units': [
                {
                    'id': u.id,
                    'type': u.type,
                    'health': u.health,
                    'strength': u.strength,
                    'location': self.get_location_of_unit(u.id).name
                } for u in team.units
            ],
            'locations': {}
        }
        for loc in self.locations:
            loc_dict = {
                'control': loc.control,
                'resources': loc.resources,
                'connections': loc.connections,
                'own_units_count': len(loc.units.get(team_name, [])),
            }
            visible = len(loc.units.get(team_name, [])) > 0
            if not visible:
                for conn_name in loc.connections:
                    conn_loc = self.get_location_by_name(conn_name)
                    if conn_loc and len(conn_loc.units.get(team_name, [])) > 0:
                        visible = True
                        break
            if visible:
                loc_dict['enemy_units_count'] = len(loc.units.get(opponent_name, []))
            else:
                loc_dict['enemy_units_count'] = None
            state['locations'][loc.name] = loc_dict
        return state

    def execute_actions(self, team_name, actions):
        results = []
        team = self.teams[team_name]
        opponent_name = 'Red' if team_name == 'Blue' else 'Blue'

        for action in actions:
            action_type = action.get('type')

            if action_type == 'reinforce':
                loc_name = action.get('location')
                loc = self.get_location_by_name(loc_name)
                if loc and loc.control == team_name and team.resources >= 3:
                    team.resources -= 3
                    new_id = f"{team_name}-{len(team.units) + 1}"
                    new_unit = Unit(new_id, 'infantry', 3, 1)
                    team.units.append(new_unit)
                    loc.units.setdefault(team_name, []).append(new_unit)
                    results.append(f'Reinforced {loc_name} with new unit {new_id}')
                else:
                    results.append(f'Failed to reinforce {loc_name}')

            elif action_type == 'move':
                unit_id = action.get('unit_id')
                to_name = action.get('to')

                if not unit_id or not to_name:
                    results.append(f'Invalid move action: {action}')
                    continue

                unit = self.get_unit_by_id(unit_id)
                if not unit or unit not in team.units:
                    results.append(f'Unit {unit_id} not found or does not belong to team {team_name}')
                    continue
                
                from_loc = self.get_location_of_unit(unit_id)
                if not from_loc:
                    results.append(f'Unit {unit_id} location not found')
                    continue

                if to_name not in from_loc.connections:
                    results.append(f'Invalid move for {unit_id}: {to_name} is not adjacent to {from_loc.name}')
                    continue

                to_loc = self.get_location_by_name(to_name)
                if not to_loc:
                    results.append(f'Invalid move destination: {to_name}')
                    continue

                # Execute the move
                results.append(f'Moving {unit_id} from {from_loc.name} to {to_name}')
                
                # Remove unit from its current location
                if team_name in from_loc.units and unit in from_loc.units[team_name]:
                    from_loc.units[team_name].remove(unit)
                else:
                    # This case should ideally not happen if state is consistent
                    results.append(f'Error: Unit {unit_id} not found in {from_loc.name} unit list.')
                    continue

                # Check for combat
                def_units = to_loc.units.get(opponent_name, [])[:]
                if not def_units:
                    # No combat, move in
                    to_loc.units.setdefault(team_name, []).append(unit)
                    old_control = to_loc.control
                    if old_control != team_name:
                        to_loc.control = team_name
                        if old_control:
                            self.teams[old_control].controlled_locations.remove(to_name)
                        team.controlled_locations.append(to_name)
                    results.append(f'Successfully moved to {to_name}, control: {to_loc.control}')
                else:
                    # Combat
                    att_units = [unit]
                    combat_log = [f'Combat at {to_name}: {len(att_units)} attackers vs {len(def_units)} defenders']
                    combat_rounds = 0
                    while att_units and def_units and combat_rounds < 100:
                        att_strength = sum(u.strength for u in att_units)
                        def_strength = sum(u.strength for u in def_units)
                        att_roll = random.randint(1, 6) + att_strength
                        def_roll = random.randint(1, 6) + def_strength

                        if att_roll > def_roll:
                            lost_unit = random.choice(def_units)
                            lost_unit.health -= 1
                            if lost_unit.health <= 0:
                                def_units.remove(lost_unit)
                                self.teams[opponent_name].units.remove(lost_unit)
                                combat_log.append(f'Defender unit {lost_unit.id} eliminated')
                        elif def_roll > att_roll:
                            lost_unit = random.choice(att_units)
                            lost_unit.health -= 1
                            if lost_unit.health <= 0:
                                att_units.remove(lost_unit)
                                team.units.remove(lost_unit)
                                combat_log.append(f'Attacker unit {lost_unit.id} eliminated')
                        combat_rounds += 1
                    
                    results.extend(combat_log)
                    results.append(f'Combat result: {len(att_units)} attackers left, {len(def_units)} defenders left')

                    to_loc.units[opponent_name] = def_units
                    if att_units:
                        to_loc.units.setdefault(team_name, []).extend(att_units)
                        old_control = to_loc.control
                        if old_control != team_name:
                            to_loc.control = team_name
                            if old_control:
                                self.teams[old_control].controlled_locations.remove(to_name)
                            if to_name not in team.controlled_locations:
                                team.controlled_locations.append(to_name)
                    
        # Collect resources at the end of the turn
        resources_gained = sum(self.get_location_by_name(loc).resources for loc in team.controlled_locations)
        team.resources += resources_gained
        results.append(f'Gained {resources_gained} resources, total: {team.resources}')

        return results

    def get_full_state(self):
        state = {
            'turn': self.turn,
            'teams': {},
            'locations': {}
        }
        for team_name, team in self.teams.items():
            state['teams'][team_name] = {
                'model': TEAM_MODELS.get(team_name, team_name),
                'resources': team.resources,
                'controlled_locations': team.controlled_locations,
                'units': [{
                    'id': u.id,
                    'type': u.type,
                    'health': u.health,
                    'strength': u.strength,
                    'location': self.get_location_of_unit(u.id).name
                } for u in team.units]
            }
        for loc in self.locations:
            loc_dict = {
                'control': loc.control,
                'resources': loc.resources,
                'connections': loc.connections,
                'units': {t: len(us) for t, us in loc.units.items()}
            }
            state['locations'][loc.name] = loc_dict
        return state

    def check_victory(self):
        for team_name in ['Blue', 'Red']:
            team = self.teams[team_name]
            opponent = self.teams['Red' if team_name == 'Blue' else 'Blue']
            if len(team.controlled_locations) >= 5 or len(opponent.units) == 0:
                return team_name
        return None