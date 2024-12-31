"""A collection of restream servers and the questions asked of it."""

from src.domain.core.errors import ValidationError
from src.domain.servers.lifecycle import READY, RestreamServer, STATES
from src.domain.servers.region import latency_millis, normalize_region


class ServerPool:
    """Every server the studio currently holds."""

    __slots__ = ("servers",)

    def __init__(self, servers=()):
        materialised = tuple(servers)
        for server in materialised:
            if not isinstance(server, RestreamServer):
                raise ValidationError("pool holds RestreamServers", field="servers")
        names = [server.name for server in materialised]
        if len(set(names)) != len(names):
            raise ValidationError("duplicate server in the pool", field="servers")
        self.servers = materialised

    def with_server(self, server):
        return ServerPool(self.servers + (server,))

    def without(self, name):
        return ServerPool(server for server in self.servers if server.name != name)

    def replace(self, server):
        """Swap in an updated copy of a server already in the pool."""
        found = False
        updated = []
        for existing in self.servers:
            if existing.name == server.name:
                updated.append(server)
                found = True
            else:
                updated.append(existing)
        if not found:
            raise ValidationError("server is not in the pool", field="server")
        return ServerPool(updated)

    def find(self, name, default=None):
        for server in self.servers:
            if server.name == name:
                return server
        return default

    def for_subscription(self, reference):
        return tuple(
            server
            for server in self.servers
            if server.subscription_reference == reference
        )

    def in_state(self, state):
        if state not in STATES:
            raise ValidationError("unknown state {}".format(state), field="state")
        return tuple(server for server in self.servers if server.state == state)

    def usable(self):
        return self.in_state(READY)

    def in_region(self, region):
        wanted = normalize_region(region)
        return tuple(server for server in self.servers if server.region == wanted)

    def with_room(self, wanted=1):
        return tuple(server for server in self.servers if server.has_room(wanted))

    def total_capacity(self):
        return sum(server.capacity for server in self.usable())

    def total_assigned(self):
        return sum(server.assigned for server in self.servers)

    def utilisation_percent(self):
        capacity = self.total_capacity()
        if capacity == 0:
            return 0.0
        return round(self.total_assigned() * 100.0 / capacity, 2)

    def nearest_usable(self, origin, wanted=1):
        """The usable server with room that is closest to ``origin``."""
        candidates = [server for server in self.usable() if server.has_room(wanted)]
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda server: (latency_millis(origin, server.region), server.name),
        )[0]

    def to_dict(self):
        return {
            "servers": [server.to_dict() for server in self.servers],
            "capacity": self.total_capacity(),
            "assigned": self.total_assigned(),
            "utilisation_percent": self.utilisation_percent(),
        }

    def __len__(self):
        return len(self.servers)

    def __iter__(self):
        return iter(self.servers)

    def __eq__(self, other):
        return isinstance(other, ServerPool) and other.servers == self.servers

    def __hash__(self):
        return hash(("pool", self.servers))

    def __repr__(self):
        return "ServerPool({} servers)".format(len(self.servers))
