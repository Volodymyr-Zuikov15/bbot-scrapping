from bbot.modules.base import BaseModule


class portscanner(BaseModule):
    """
    A portscanner containing useful methods for nmap, masscan, etc.
    """

    async def setup(self):
        self.ip_ranges = [e.host for e in self.scan.target.events if e.type == "IP_RANGE"]
        exclude, invalid_exclude = self._build_targets(self.scan.blacklist)
        self.exclude_file = None
        if exclude:
            self.exclude_file = self.helpers.tempfile(exclude, pipe=False)
        if invalid_exclude > 0:
            self.warning(
                f"Port scanner can only accept IP addresses or IP ranges as blacklist ({invalid_exclude:,} blacklisted were hostnames)"
            )
        return True

    async def filter_event(self, event):
        """
        The purpose of this filter_event is to decide whether we should accept individual IP_ADDRESS
        events that reside inside our target subnets (IP_RANGE), if any.

        This prevents scanning the same IP twice.
        """
        # if we are emitting hosts from a previous asset_inventory, this is a special case
        # in this case we want to accept the individual IPs even if they overlap with our target ranges
        asset_inventory_module = self.scan.modules.get("asset_inventory", None)
        asset_inventory_config = getattr(asset_inventory_module, "config", {})
        asset_inventory_use_previous = asset_inventory_config.get("use_previous", False)
        if event.type == "IP_ADDRESS" and not asset_inventory_use_previous:
            for net in self.helpers.ip_network_parents(event.data, include_self=True):
                if net in self.ip_ranges:
                    return False, f"skipping {event.host} because it is already included in {net}"
        elif event.type == "IP_RANGE" and asset_inventory_use_previous:
            return False, f"skipping IP_RANGE {event.host} because asset_inventory.use_previous=True"
        return True

    def _build_targets(self, target, delimiter=","):
        invalid_targets = 0
        targets = []
        for t in target:
            t = self.helpers.make_ip_type(t.data)
            if isinstance(t, str):
                invalid_targets += 1
            else:
                if self.helpers.is_ip(t):
                    targets.append(f"{t}/32")
                else:
                    targets.append(str(t))
        return targets, invalid_targets
