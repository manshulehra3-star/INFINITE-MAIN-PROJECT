"""InfiniteCore Bot — Pterodactyl Panel API Client"""
import aiohttp
from typing import Optional, Dict, Any
from .. import config as C


class PterodactylAPI:
    """Async wrapper for Pterodactyl Application API."""

    def __init__(self, url: str = "", key: str = ""):
        self.url = (url or C.PTERO_PANEL_URL).rstrip("/")
        self.key = key or C.PTERO_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _enabled(self) -> bool:
        return bool(self.url and self.key)

    async def _req(self, method: str, endpoint: str, data: Optional[dict] = None):
        if not self._enabled():
            return {"error": "Pterodactyl not configured"}
        url = f"{self.url}/api/application/{endpoint}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.request(
                    method, url, headers=self.headers, json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as r:
                    if r.status == 204:
                        return {"ok": True}
                    try:
                        return await r.json()
                    except:
                        return {"error": f"HTTP {r.status}"}
        except Exception as e:
            return {"error": str(e)}

    # ─── Users ───
    async def create_user(self, email: str, username: str,
                          first: str, last: str, password: str):
        return await self._req("POST", "users", {
            "email": email, "username": username,
            "first_name": first, "last_name": last, "password": password,
        })

    async def get_user(self, user_id: int):
        return await self._req("GET", f"users/{user_id}")

    async def list_users(self):
        return await self._req("GET", "users")

    # ─── Servers ───
    async def create_server(self, name: str, user_id: int, egg_id: int,
                            docker_image: str, startup: str,
                            environment: Dict[str, str],
                            ram: int, cpu: int, disk: int,
                            memory_overallocate: int = 0,
                            disk_overallocate: int = 0):
        payload = {
            "name": name,
            "user": user_id,
            "egg": egg_id,
            "docker_image": docker_image,
            "startup": startup,
            "environment": environment,
            "limits": {
                "memory": ram,
                "swap": 0,
                "disk": disk,
                "io": 500,
                "cpu": cpu,
            },
            "feature_limits": {
                "databases": 5,
                "allocations": 3,
                "backups": 5,
            },
            "deploy": {
                "locations": [C.PTERO_NODE_ID],
                "dedicated_ip": False,
                "port_range": [],
            },
        }
        return await self._req("POST", "servers", payload)

    async def get_server(self, server_id: int):
        return await self._req("GET", f"servers/{server_id}")

    async def list_servers(self):
        return await self._req("GET", "servers")

    async def delete_server(self, server_id: int):
        return await self._req("DELETE", f"servers/{server_id}")

    async def suspend_server(self, server_id: int):
        return await self._req("POST", f"servers/{server_id}/suspend")

    async def unsuspend_server(self, server_id: int):
        return await self._req("POST", f"servers/{server_id}/unsuspend")

    async def reinstall_server(self, server_id: int):
        return await self._req("POST", f"servers/{server_id}/reinstall")

    # ─── Nodes ───
    async def list_nodes(self):
        return await self._req("GET", "nodes")

    async def get_node(self, node_id: int):
        return await self._req("GET", f"nodes/{node_id}")

    # ─── Eggs ───
    async def list_eggs(self):
        return await self._req("GET", "nests")

    async def list_eggs_in_nest(self, nest_id: int):
        return await self._req("GET", f"nests/{nest_id}/eggs")

    async def get_egg(self, nest_id: int, egg_id: int):
        return await self._req("GET", f"nests/{nest_id}/eggs/{egg_id}")

    # ─── Allocations ───
    async def list_allocations(self, node_id: int):
        return await self._req("GET", f"nodes/{node_id}/allocations")

    async def create_allocation(self, node_id: int, ip: str, port: int):
        return await self._req("POST", f"nodes/{node_id}/allocations", {
            "ip": ip, "ports": [str(port)]
        })

    # ─── Health ───
    async def health(self) -> dict:
        r = await self._req("GET", "nodes")
        if "error" in r:
            return {"ok": False, "error": r["error"]}
        return {"ok": True, "nodes": len(r.get("data", []))}


# Singleton
ptero = PterodactylAPI()
