####################################################
# LSrouter.py
# Name:
# HUID:
#####################################################

from router import Router
from packet import Packet

import json
import heapq

class LSrouter(Router):
    """Link state routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0

        self.sequence_number = 0 
        self.link_state = {}
        self.lsdb = {}
        self.forwarding_table = {}

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        # TODO
        if packet.is_traceroute:
            end_port = packet.dst_addr
            if end_port in self.forwarding_table:
                out_port = self.forwarding_table[end_port][0]
                self.send(out_port, packet)
                return
        else:
            src_addr = packet.src_addr
            sequence_number, link_state = json.loads(packet.content)
            previous_link_state = self.lsdb.get(src_addr)
            if previous_link_state is None or sequence_number > previous_link_state['sequence_number']:
                self.lsdb[src_addr] = {
                    'sequence_number': sequence_number, 
                    'link_state': link_state
                }
                self.compute_forwarding_table()
                for p, (nbr, _) in self.link_state.items():
                    if p != port:
                        content_str = json.dumps((sequence_number, link_state))
                        copy_packet = Packet(Packet.ROUTING, self.addr, nbr, content=content_str)
                        self.send(p, copy_packet)

    def broadcast_lsa(self):
        links = {nbr: cost for (_, (nbr, cost)) in self.link_state.items()}
        self.lsdb[self.addr] = (self.sequence_number, links.copy())
        lsa_content = json.dumps((self.sequence_number, links))
        for port, (neighbor, _) in self.link_state.items():
            pkt = Packet(Packet.ROUTING, self.addr, neighbor, content=lsa_content)
            self.send(port, pkt)

    def handle_new_link(self, port, endpoint, cost):
        self.link_state[port] = (endpoint, cost)
        self.sequence_number += 1
        self.broadcast_lsa()
        self.compute_forwarding_table()

    def handle_remove_link(self, port):
        if port in self.link_state:
            del self.link_state[port]
            self.sequence_number += 1
            self.broadcast_lsa()
            self.compute_forwarding_table()

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.sequence_number += 1
            self.broadcast_lsa()
            self.compute_forwarding_table()

    def compute_forwarding_table(self):
        graph = {router: links.copy() for router, (_, links) in self.lsdb.items()}
        dist = {self.addr: 0}
        prev = {}
        heap = [(0, self.addr)]
        visited = set()
        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)
            for v, w in graph.get(u, {}).items():
                new_cost = d + w
                if v not in dist or new_cost < dist[v]:
                    dist[v] = new_cost
                    prev[v] = u
                    heapq.heappush(heap, (new_cost, v))
       
        self.forwarding_table.clear()
        for dest, total_cost in dist.items():
            if dest == self.addr:
                continue
            next_hop = dest
            while prev.get(next_hop) != self.addr:
                next_hop = prev.get(next_hop)
                if next_hop is None:
                    break
            if next_hop is None:
                continue
            for port, (nbr, _) in self.link_state.items():
                if nbr == next_hop:
                    self.forwarding_table[dest] = (port, total_cost)
                    break

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        # TODO
        #   NOTE This method is for your own convenience and will not be graded
        return f"LSrouter(addr={self.addr}, ft={self.forwarding_table})"
