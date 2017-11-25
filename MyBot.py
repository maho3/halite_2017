
import hlt
import logging
import time


game = hlt.Game("Settler_v5")
logging.info("Starting my Settler bot!")

# set constants
dweight = 5     # weight for distance in planet heuristic
midgame = 0.6   # proportion of planets owned in midgame
lategame = 0.8  # proportion of planets owned in lategame
maxdef = 2      # max number of defenders per planet

me = None


""" 
 TODO: Add comments
       Only send (# of docks) + (# of enemies) to each planet, max
       Add navigation
 """

def in_orbit(planet, ship):
    return (planet.calculate_distance_between(ship) < (planet.radius + 2*hlt.constants.DOCK_RADIUS + hlt.constants.SHIP_RADIUS))

while True:
    # grab data and initialize
    game_map = game.update_map()
    command_queue = []
    
    # grab useful information
    me = game_map.get_me()
    players = game_map.all_players()
    
    planets = game_map.all_planets()
    my_planets = [planet for planet in planets if (planet.owner == me)]
    
    my_ships = me.all_ships()
    my_undocked_ships = [myship for myship in my_ships if (myship.docking_status == myship.DockingStatus.UNDOCKED)]
    
    they_ships = [ship for they in game_map.all_players() if they!=me for ship in they.all_ships()]
    all_ships = my_ships + they_ships
    
    maxRad = max(planet.radius for planet in planets)
    

    
    # check if how many are owned (stage of game)
    owned = 0
    for planet in planets:
        if planet.is_owned():
            owned += 1
            
    # flee command
    if (owned > lategame*len(planets)) and (len(my_undocked_ships) < 0.1*len(all_ships)):
        for ship in my_undocked_ships:
            navigate_command = ship.navigate(
                hlt.entity.Position(0,0),
                game_map,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=False)
                
            if navigate_command is not None:
                command_queue.append(navigate_command)
                
        game.send_command_queue(command_queue)
        continue
    
    # initialize calculated variables
    atms_me = {}
    atms_them = {} 
    atms_all = {}
    in_orbit_me = {}
    in_orbit_them = {}
    defenders = []
    
    t0 = time.time()
    for planet in planets:
        # ships sorted by distance to each planet
        atms_me[planet.id] = sorted(my_ships, key=lambda p: planet.calculate_distance_between(p))
        atms_them[planet.id] = sorted(they_ships, key=lambda p: planet.calculate_distance_between(p))
        #atms_all[planet.id] = sorted(all_ships, key=lambda p: planet.calculate_distance_between(p))
        
        # find how many ships are close to the surface
        in_orbit_me[planet.id] = 0
        in_orbit_them[planet.id] = 0
        
        for atms in atms_me[planet.id]:
            if in_orbit(planet,atms):
                in_orbit_me[planet.id] += 1
            else:
                break
                
        for atms in atms_them[planet.id]:
            if in_orbit(planet,atms):
                in_orbit_them[planet.id] += 1
            else:
                break
                
        # assign maxdef defenders
        for i in range(maxdef):
            if (planet.owner == me) and (i < in_orbit_them[planet.id]):
                # get closest undocked ship to defend
                if len(all_ships) > 100:
                    try:
                        shipd = next(ship for ship in atms_me[planet.id] if ((ship.docking_status == ship.DockingStatus.UNDOCKED) and (ship.id not in defenders)))
                    except StopIteration:
                        break
                else:
                    shipd_free = [myship for myship in my_undocked_ships if (myship.id not in defenders)]
                
                    if len(shipd_free)==0:
                        break
                    
                    shipd = min(shipd_free, key = lambda p: atms_them[planet.id][i].calculate_distance_between(p))
                
                navigate_command = shipd.navigate(
                    shipd.closest_point_to(atms_them[planet.id][i]),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=len(my_planets) > len(planets)/float(len(players)))
                    
                if navigate_command is not None:
                    command_queue.append(navigate_command)
                    defenders.append(shipd.id)
            else:
                break
    defendt = time.time() - t0
    
    t0 = time.time()                
    for ship in my_undocked_ships:
        navigate_command=None
        
        """if ship.docking_status != ship.DockingStatus.UNDOCKED:
            continue"""
            
        if ship.id in defenders:
            continue
        
        # approach planets by heuristic
        planetlist = sorted(planets, 
                            key= lambda planet: ship.calculate_distance_between(planet)*(dweight - float(planet.radius)/maxRad))
        
        for planet in planetlist:
            if planet.owner == me:
                
                if planet.is_full(): # if its full and i own it, ignore
                    continue

                elif owned < lategame * len(planets): # expand fast in early game
                    if len(my_planets) < (midgame*len(planets))/len(players):
                        continue 
                             
            if len(all_ships) > 50: # ignore ships if danger of timing out
                ignore_s = (in_orbit_me[planet.id] + in_orbit_them[planet.id]) > 10
            else:
                ignore_s = False
                
            if in_orbit(planet, ship):
                if (not (planet.owner == me)):
                    if planet.is_owned(): # attack enemy docked ships 
                        near_dock = min(planet.all_docked_ships(),
                                            key= lambda dock: ship.calculate_distance_between(dock))
                        
                        navigate_command = ship.navigate(
                            ship.closest_point_to(near_dock),
                            game_map,
                            speed=int(hlt.constants.MAX_SPEED),
                            ignore_ships=ignore_s)
     

                    
                    elif ship.can_dock(planet): # if i can dock, steal it

                        if atms_them[planet.id][0].can_dock(planet):
                            navigate_command = ship.navigate(
                                ship.closest_point_to(atms_them[planet.id][0]),
                                game_map,
                                speed=int(hlt.constants.MAX_SPEED),
                                ignore_ships=True)
                        else:
                            command_queue.append(ship.dock(planet))
                        
                            break
                            
                    if navigate_command is not None:
                        command_queue.append(navigate_command)
                        break
                else:
                    """if in_orbit_them[planet.id] > maxdef: # if they're around my planet, go get em
                        navigate_command = ship.navigate(
                            ship.closest_point_to(atms_them[planet.id][maxdef]),
                            game_map,
                            speed=int(hlt.constants.MAX_SPEED),
                            ignore_ships=ignore_s)"""
                        
                    if ship.can_dock(planet): # otherwise dock at my planets
                        command_queue.append(ship.dock(planet))
                        break
                        
            if navigate_command is None: # head to best heuristic planet
                navigate_command = ship.navigate(
                    ship.closest_point_to(planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=(len(me.all_ships())>100) )

            if navigate_command is None:
                continue
            else:
                command_queue.append(navigate_command)
                
            break
    movet = time.time() - t0
    
    logging.info("Times: defend " + str(defendt) + ' ; move ' + str(movet))
    
    game.send_command_queue(command_queue)

