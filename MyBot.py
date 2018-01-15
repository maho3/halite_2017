
import hlt
import logging
import time

from matt import NodeMap, Nav, in_orbit, manage_commands

import numpy as np

game = hlt.Game("Settler_v6")
logging.info("Starting my Settler bot!")

# set constants
dweight = 5     # weight for distance in planet heuristic
midgame = 0.6   # proportion of planets owned in midgame
lategame = 0.8  # proportion of planets owned in lategame
maxdef_perc = 0.5 # percentage of undocked ships for defenders per planet

me = None


nav = Nav(moverad = hlt.constants.MAX_SPEED, 
          lookahead = 10.0, 
          anginc = np.pi*2/180.
         )


""" 
 TODO: Only send (# of docks) + (# of enemies) to each planet, max
       Add navigation
       
       
 PRIORITY: Defend my planets accordingly
        Attack new planets
 """

 
 
first = True

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
    my_docked_ships = [myship for myship in my_ships if (myship.docking_status != myship.DockingStatus.UNDOCKED)]
    
    they_ships = [ship for they in game_map.all_players() if they!=me for ship in they.all_ships()]
    all_ships = my_ships + they_ships
    
    if first:
        pmap = NodeMap(size = (game_map.width, game_map.height), spc = 0.25, shiprad = 1*hlt.constants.SHIP_RADIUS)
        pmap.setObjects(planets)
        
        first = False
    
    smap = pmap.copy()
    smap.setObjects(all_ships)
    
    maxRad = max(planet.radius for planet in planets)
    
    # dynamic settings
    if len(my_planets) > 0:
        maxdef = int(maxdef_perc*len(my_undocked_ships)/len(my_planets) + 1)
    else:
        maxdef = 0
    
    
    # check if how many are owned (stage of game)
    owned = 0
    for planet in planets:
        if planet.is_owned():
            owned += 1
            
    # flee command
    if (owned > midgame*len(planets)) and (len(my_ships) < 0.05*len(all_ships)):
        flee_pos = [hlt.entity.Position(0,0), hlt.entity.Position(game_map.width-1,0),
                    hlt.entity.Position(0,game_map.height-1), 
                    hlt.entity.Position(game_map.width-1,game_map.height-1)]
        
        for ship in my_ships:
            navigate_command = None
            if (ship.docking_status != ship.DockingStatus.UNDOCKED):
                navigate_command = (ship,'UNDOCK')
            else:
                if (ship.y <= 5) and (ship.x > 5):
                    flee_pos = hlt.entity.Position(0,3)
                elif (ship.x <= 5) and (ship.y < game_map.height - 5):
                    flee_pos = hlt.entity.Position(3,game_map.height)
                elif (ship.y >= game_map.height - 5) and (ship.x < game_map.width - 5):
                    flee_pos = hlt.entity.Position(game_map.width, game_map.height - 3)
                elif (ship.x >= game_map.width - 5) and (ship.y > 5):
                    flee_pos = hlt.entity.Position(game_map.width - 3, 0)
                else:
                    flee_pos = min( hlt.entity.Position(ship.x, 0),
                                    hlt.entity.Position(0, ship.y),
                                    hlt.entity.Position(ship.x, game_map.height),
                                    hlt.entity.Position(game_map.width, ship.y),
                                    key = lambda p: ship.calculate_distance_between(p))
                
                navigate_command = (ship, flee_pos)
                
            if navigate_command is not None:
                command_queue.append(navigate_command)
        
        command_queue = manage_commands(command_queue, pmap, smap, nav)
                
        game.send_command_queue(command_queue)
        continue
    
    # initialize calculated variables
    atms_me = {}
    atms_them = {} 
    atms_all = {}
    orbit_me = {}
    orbit_them = {}
    
    # initialize roles
    defenders = []
    orbiters = []
    supporters = []
    assigned_to = {}
    
    t0 = time.time()
    for planet in planets:
        assigned_to[planet.id] = 0
        
        # ships sorted by distance to each planet
        atms_me[planet.id] = sorted(my_ships, key=lambda p: planet.calculate_distance_between(p))
        atms_them[planet.id] = sorted(they_ships, key=lambda p: planet.calculate_distance_between(p))
        #atms_all[planet.id] = sorted(all_ships, key=lambda p: planet.calculate_distance_between(p))
        
        # find how many ships are close to the surface
        orbit_me[planet.id] = 0
        orbit_them[planet.id] = 0
        
        for atms in atms_me[planet.id]:
            if in_orbit(planet,atms):
                orbit_me[planet.id] += 1
            else:
                break
                
        for atms in atms_them[planet.id]:
            if in_orbit(planet,atms):
                orbit_them[planet.id] += 1
            else:
                break
                
        # assign maxdef defenders
        for i in range(maxdef):
            if (planet.owner == me) and (i < orbit_them[planet.id]):
                # get closest undocked ship to defend
                if len(my_ships) > 100:
                    try:
                        shipd = next(ship for ship in atms_me[planet.id] if ((ship.docking_status == ship.DockingStatus.UNDOCKED) and (ship.id not in defenders)))
                    except StopIteration:
                        break
                else:
                    shipd_free = [myship for myship in my_undocked_ships if (myship.id not in defenders)]
                
                    if len(shipd_free)==0:
                        break
                    
                    shipd = min(shipd_free, key = lambda p: atms_them[planet.id][i].calculate_distance_between(p))
                
                navigate_command = (shipd, atms_them[planet.id][i])
                    
                if navigate_command is not None:
                    command_queue.append(navigate_command)
                    
                    defenders.append(shipd.id)
                    assigned_to[planet.id] += 1
            else:
                break
    defendt = time.time() - t0
    
    t0 = time.time()
    
    for ship in my_undocked_ships:
        navigate_command = None
        
        if ship.id in defenders:
            continue
        if ship.id in orbiters:
            continue
        if ship.id in supporters:
            continue
        
        for planet in planets:
            if not in_orbit(planet,ship):
                continue
                
            if (planet.owner == me):
                if planet.is_full():
                    continue
                if (owned < lategame * len(planets)) and (len(my_ships) >= 3): # expand fast in early game
                    if len(my_planets) < (midgame*len(planets))/len(players):
                        continue
                        
                if ship.can_dock(planet): # otherwise dock at my planets
                    command_queue.append((ship,'DOCK',planet))
                    
                    assigned_to[planet.id] += 1
                    orbiters.append(ship.id)
                    break
                
            if (not (planet.owner == me)):
                if planet.is_owned(): # attack enemy docked ships 
                    near_dock = min(planet.all_docked_ships(),
                                        key= lambda dock: ship.calculate_distance_between(dock))
                    
                    navigate_command = (ship,near_dock)
                
                elif ship.can_dock(planet): # if i can dock, steal it
                    
                    if atms_them[planet.id][0].can_dock(planet):
                        navigate_command = (ship,atms_them[planet.id][0])
                    else:
                        navigate_command = (ship, 'DOCK', planet)
                        
                if navigate_command is not None:
                    command_queue.append(navigate_command)
                    
                    assigned_to[planet.id] += 1
                    orbiters.append(ship.id)
                    break
            else:
                """if orbit_them[planet.id] > maxdef: # if they're around my planet, go get em
                    navigate_command = ship.navigate(
                        ship.closest_point_to(atms_them[planet.id][maxdef]),
                        game_map,
                        speed=int(hlt.constants.MAX_SPEED),
                        ignore_ships=ignore_s)"""

    if len(my_planets) > (lategame*len(planets))/len(players):
        need_support = {}
        for planet in my_planets:
            need_support[planet.id] = (planet.num_docking_spots - len(planet.all_docked_ships()) + orbit_them[planet.id]) - assigned_to[planet.id]
            
        sup_planets = sorted(my_planets, key = lambda p: need_support[p.id], reverse=True)
            
        for planet in sup_planets:
            
            if need_support[planet.id] > 0:
                supgen = []
                for ship in atms_me[planet.id]:
                    if (ship.docking_status != ship.DockingStatus.UNDOCKED) | (ship.id in defenders) | (ship.id in orbiters) | (ship.id not in supporters):
                        continue
                    else:
                        supgen.append(ship)
                
                for i in range(need_support[planet.id]):
                    navigate_command = None
                    
                    if len(supgen) <= i:
                        break
                    
                    ship_sup = supgen[i]
                        
                    navigate_command = (ship_sup,planet)
                        
                    if navigate_command is not None:
                        command_queue.append(navigate_command)
                        
                        assigned_to[planet.id] += 1
                        supporters.append(ship.id)
            else:
                break
                    
    for ship in my_undocked_ships:
        navigate_command=None
            
        if ship.id in defenders:
            continue
        if ship.id in orbiters:
            continue
        if ship.id in supporters:
            continue
        
        # approach planets by heuristic
        planetlist = sorted(planets, 
                            key= lambda planet: ship.calculate_distance_between(planet)*(dweight - float(planet.radius)/maxRad))
        
        for planet in planetlist:
            if planet.owner == me:
                continue
                if planet.is_full(): # if its full and i own it, ignore
                    continue

                elif (owned < lategame * len(planets)) and (len(my_ships) > 3): # expand fast in early game
                    if len(my_planets) < (midgame*len(planets))/len(players):
                        continue 
                             
            if navigate_command is None: # head to best heuristic planet
                speed = hlt.constants.MAX_SPEED
                
                navigate_command = (ship,planet)

            if navigate_command is None:
                continue
            else:
                command_queue.append(navigate_command)
                
            break
            
    movet = time.time() - t0
    
    logging.info("Times: defend " + str(defendt) + ' ; move ' + str(movet))
    logging.info(str(defenders) + ' ~~~ ' + str(orbiters) + ' ~~~ ' + str(supporters))
    
    command_queue = manage_commands(command_queue, pmap, smap, nav)
    
    game.send_command_queue(command_queue)

