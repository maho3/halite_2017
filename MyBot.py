
import hlt
import logging



game = hlt.Game("Settler_v4")
logging.info("Starting my Settler bot!")

dweight = 5

me = None

while True:
    game_map = game.update_map()
    command_queue = []
    
    me = game_map.get_me()
    planets = game_map.all_planets()
    my_planets = [planet for planet in planets if (planet.owner == me)]
    
    my_ships = me.all_ships()
    they_ships = [ship for they in game_map.all_players() if they!=me for ship in they.all_ships()]
    all_ships = my_ships + they_ships
    
    maxRad = max(planet.radius for planet in planets)
    
    all_owned = True
    for planet in planets:
        if (not planet.is_owned()):
            all_owned = False
            break
            
    atms_me = {}
    atms_them = {} 
    atms_all = {}
    defenders = []   
    for planet in planets:
        atms_me[planet.id] = sorted(my_ships, key=lambda p: planet.calculate_distance_between(p))
        atms_them[planet.id] = sorted(they_ships, key=lambda p: planet.calculate_distance_between(p))
        atms_all[planet.id] = sorted(all_ships, key=lambda p: planet.calculate_distance_between(p))
        
        if (planet.owner == me) and (planet.calculate_distance_between(atms_them[planet.id][0])< (planet.radius + hlt.constants.DOCK_RADIUS + hlt.constants.SHIP_RADIUS)):
            try:
                shipd = next(ship for ship in atms_me[planet.id] if ((ship.docking_status == ship.DockingStatus.UNDOCKED) and (ship.id not in defenders)))
            except StopIteration:
                continue
            
            navigate_command = shipd.navigate(
                shipd.closest_point_to(atms_them[planet.id][0]),
                game_map,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=False)
                
            if navigate_command is not None:
                command_queue.append(navigate_command)
                defenders.append(shipd.id)
                        
    for ship in my_ships:
        navigate_command=None
        
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            continue
            
        if ship.id in defenders:
            continue
        
        planetlist = sorted(planets, 
                            key= lambda planet: ship.calculate_distance_between(planet)*(dweight - float(planet.radius)/maxRad))
        
        for planet in planetlist:
            if planet.owner == me:
                
                if planet.is_full():
                    continue

                elif not all_owned:
                    if len(my_planets) < 4:
                        continue

            if ship.can_dock(planet):
                if (planet.is_owned() and (not (planet.owner == me))):
                    near_dock = min(planet.all_docked_ships(),
                                        key= lambda dock: ship.calculate_distance_between(dock))
                    
                    if len(atms_all[planet.id]) > 50:
                        ignore_s = planet.calculate_distance_between(atms_all[planet.id][20]) < (planet.radius + 2*hlt.constants.DOCK_RADIUS)
                    else:
                        ignore_s = False
                    
                    navigate_command = ship.navigate(
                        ship.closest_point_to(near_dock),
                        game_map,
                        speed=int(hlt.constants.MAX_SPEED),
                        ignore_ships=ignore_s)
                else: 
                    command_queue.append(ship.dock(planet))
                    break
            else:
                navigate_command = ship.navigate(
                    ship.closest_point_to(planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=(len(me.all_ships())>100) )

            if navigate_command is not None:
                command_queue.append(navigate_command)
                
            break

    game.send_command_queue(command_queue)

