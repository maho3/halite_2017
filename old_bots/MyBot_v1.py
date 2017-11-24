
import hlt
import logging


game = hlt.Game("Settler_v1")
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

            if (not all_owned) and (planet.is_owned()):
                continue

            if ship.can_dock(planet):
                command_queue.append(ship.dock(planet))
            else:
                navigate_command = ship.navigate(
                    ship.closest_point_to(planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=False)

                if navigate_command:
                    command_queue.append(navigate_command)
            break

    game.send_command_queue(command_queue)

