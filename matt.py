import numpy as np
import hlt
import logging


def in_orbit(planet, ship):
    return (planet.calculate_distance_between(ship) < (planet.radius + 2*hlt.constants.DOCK_RADIUS + hlt.constants.SHIP_RADIUS))

def manage_commands(command_queue, pmap, smap, nav):
    out_queue = []
 
     
    for com in command_queue:
        if com[1] == 'UNDOCK':
            out_queue.append(com[0].undock())
        elif com[1] == 'DOCK':
            if smap.hmap[smap.pos_to_idx((com[0].x, com[0].y))]:
                command_queue.append((com[0], com[2]))
                continue
            else:
                
                out_queue.append(com[0].dock(com[2]))
                smap.setObjects([com[0]])
        else:
            if com[1] is hlt.entity.Position:
                end_r = 0
            elif com[1] is hlt.entity.Ship:
                end_r = pmap.shiprad
            else:
                end_r = com[1].radius
            
            ang,d = nav.get_nav((com[0].x, com[0].y), (com[1].x, com[1].y),
                                end_r,
                                pmap,
                                smap
                               )
            
            out_queue.append(com[0].thrust(d,ang))
    return out_queue


class Mock:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class NodeMap:
    def __init__(self, size, spc, shiprad, hmap = None):
        self.dim = (int(size[0]/spc),int(size[1]/spc))
        self.size = size
        self.spc = self.size[0]/self.dim[0] # Lossless: Sqrt(2)*shiprad
        self.shiprad = shiprad
        
        
        if hmap is None:
            self.hmap = np.zeros(self.dim, dtype=bool)
        else:
            self.hmap = hmap
            
    def pos_to_idx(self,pos):
        return (int(pos[0]/self.spc + 0.5),int(pos[1]/self.spc + 0.5))
    def idx_to_pos(self,idx):
        return (self.spc*idx[0], self.spc*idx[1])
    
    def setObjects(self, objects):
        for o in objects:
            if o is hlt.entity.Planet:
                rad = o.radius
            else: 
                rad = self.shiprad
                
            unitrad = int((rad + self.shiprad)/self.spc+1)
                
            c = (o.x,o.y)
            cnode = self.idx_to_pos(self.pos_to_idx(c))
            
            for m in (self.spc*np.arange(-unitrad,unitrad+1) + cnode[0]):
                for n in (self.spc*np.arange(-unitrad,unitrad+1) + cnode[1]):
                    if ((((m - c[0])**2 + (n-c[1])**2)<=(rad + self.shiprad)**2) and
                        (m>=0) and (n>=0) and (m<=self.size[0]) and (n<=self.size[1])):
                        self.hmap[int(m/self.spc + 0.5),int(n/self.spc + 0.5)] = True
            
    def checkline(self, pos1, pos2): # checks line in hmap between two points to be empty
        angle = np.arctan2((pos2[1]-pos1[1]),(pos2[0]-pos1[0]))
        length_i = np.sqrt((pos2[1]-pos1[1])**2 + (pos2[0]-pos1[0])**2)/(np.sqrt(2)*self.spc)
        
        xdl = np.sqrt(2) * self.spc * np.cos(angle)
        ydl = np.sqrt(2) * self.spc * np.sin(angle)
        
        i = int(1 + self.shiprad/(np.sqrt(2)*self.spc))
        
        while i < length_i + 1:
            if self.hmap[self.pos_to_idx((pos1[0] + i*xdl, pos1[1] + i*ydl))]:
                return False
            
            i+=1
            
        return True
    
    def markline(self, pos1, angle, d):
        d_i = d/(np.sqrt(2)*self.spc)
        
        xdl = np.sqrt(2) * self.spc * np.cos(angle)
        ydl = np.sqrt(2) * self.spc * np.sin(angle)
        
        i = 0
        
        markers = []
        while i < d_i+1:
            markers.append(Mock(pos1[0] + i*xdl, pos1[1] + i*ydl))
            
            i+=1
            
        self.setObjects(markers)
        
    def copy(self):
        return NodeMap(self.size,self.spc, self.shiprad, hmap = self.hmap.copy())
        
        
class Nav:
    def __init__(self, moverad, lookahead, anginc):
        self.moverad = moverad
        self.lookahead = lookahead
        self.anginc = anginc
        
    def orient(self, cmap, start, angle, d): # finds closest empty angle and distance to target
        if cmap.checkline(start,
                          (start[0] + d*np.cos(angle),
                           start[1] + d*np.sin(angle)
                          )
                         ):
            return angle, d
        
        
        offangle = self.anginc
        checkrad = d*(1+np.cos(offangle))/2
        
        side = 1
        
        while offangle < np.pi:
            if cmap.checkline(start, 
                              (start[0] + checkrad*np.cos(angle + side*offangle),
                               start[1] + checkrad*np.sin(angle + side*offangle)
                              ) 
                             ):
                return angle+side*offangle , checkrad
            
            if side==1:
                side = -1
            else:
                side = 1
                offangle += self.anginc
                checkrad = d*(1+np.cos(offangle))/2
        
        return 0,0 #None
    
    def dist(self,node1, node2):
        return np.sqrt((node1[0]-node2[0])**2 + (node1[1]-node2[1])**2)
    
    def get_nav(self, start, end, end_r, pmap, smap): # returns angle and distance from start and end parameters
        dist = self.dist(start, end)
        ang_orig =  np.arctan2((end[1]-start[1]),(end[0]-start[0]))
        
        if smap.hmap[smap.pos_to_idx((start[0], start[1]))]:
            return int(ang_orig*180/np.pi), min(self.moverad, dist)
        
        probe_d =  dist - end_r - pmap.shiprad - 3.
        if probe_d<0:
            probe_d = 0
            
        if self.lookahead < probe_d:
            probe_d = self.lookahead
            
        ang_new, probe_d = self.orient(pmap, start, ang_orig, probe_d)
        
        if self.moverad < probe_d:
            probe_d = self.moverad
        
        ang_new, probe_d = self.orient(smap, start, ang_new, probe_d)
        
        if ang_new > ang_orig:
            ang_new = int(1 + ang_orig*180/(np.pi))
        else:
            ang_new = int(ang_orig*180/np.pi)
        
        smap.markline(start, ang_new, int(probe_d))
        
        return ang_new, probe_d
    
 
