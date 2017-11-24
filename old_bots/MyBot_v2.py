
import hlt
import logging


game = hlt.Game("Settler_v2")
logging.info("Starting my Settler bot!")

me = None

while True:
    game_map = game.update_map()
    
    me = game_map.get_me()

    command_queue = []
    
    all_owned = True
    for planet in game_map.all_planets():
        if (not planet.is_owned()):
            all_owned = False
            break
    
    for ship in me.all_ships():
        
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            continue
        
        planetlist = sorted(game_map.all_planets(), 
                            key= lambda planet: ship.calculate_distance_between(planet))
        
        for planet in planetlist:
            if (planet.is_full() and planet.owner is me):
                continue

            elif (not all_owned) and (planet.is_owned()):
                continue

            elif ship.can_dock(planet):
                if (planet.is_owned() and (not (planet.owner is me))):
                    close_dock = min(planet.all_docked_ships(),
                                        key= lambda dock: ship.calculate_distance_between(dock))
                        
                    navigate_command = ship.navigate(
                        ship.closest_point_to(close_dock),
                        game_map,
                        speed=int(hlt.constants.MAX_SPEED),
                        ignore_ships=False)
                else: 
                    command_queue.append(ship.dock(planet))
                    break
            else:
                navigate_command = ship.navigate(
                    ship.closest_point_to(planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=(len(me.all_ships())>100) )

            if navigate_command:
                command_queue.append(navigate_command)
                
            break

    game.send_command_queue(command_queue)

