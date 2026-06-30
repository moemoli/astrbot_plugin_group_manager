from astrbot.api.web import json_response, request
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_platform_adapter import (
    AiocqhttpAdapter,
)

RECALL_TYPE_KEYWORDS = "keywords"
RECALL_TYPE_CHAT_HISTORY = "chat_history"
RECALL_TYPE_LINKS = "links"
RECALL_TYPE_GROUP_RECOMMEND = "group_recommend"
RECALL_TYPE_FRIEND_RECOMMEND = "friend_recommend"
RECALL_TYPE_CARDS = "cards"

ALL_RECALL_TYPES = [
    RECALL_TYPE_KEYWORDS,
    RECALL_TYPE_CHAT_HISTORY,
    RECALL_TYPE_LINKS,
    RECALL_TYPE_GROUP_RECOMMEND,
    RECALL_TYPE_FRIEND_RECOMMEND,
    RECALL_TYPE_CARDS,
]

ACTION_WARN = "warn"
ACTION_MUTE = "mute"
ACTION_RECALL = "recall"
ACTION_KICK = "kick"
ACTION_RECALL_WARN = "recall_warn"
ACTION_RECALL_MUTE = "recall_mute"
ACTION_RECALL_KICK = "recall_kick"

ALL_VIOLATION_ACTIONS = [
    ACTION_WARN,
    ACTION_MUTE,
    ACTION_RECALL,
    ACTION_KICK,
    ACTION_RECALL_WARN,
    ACTION_RECALL_MUTE,
    ACTION_RECALL_KICK,
]

ALL_THRESHOLD_ACTIONS = [
    ACTION_WARN,
    ACTION_MUTE,
    ACTION_RECALL,
    ACTION_KICK,
    ACTION_RECALL_WARN,
    ACTION_RECALL_MUTE,
    ACTION_RECALL_KICK,
]


class GroupSetting:
    def __init__(
        self,
        enable: bool | None,
        answer: str | None,
        level: int | None,
        notify_enable: bool | None,
        notify_content: str | None,
        blacklist_enabled: bool | None = None,
        blacklist_scope: str | None = None,
        violation_recall_enabled: bool | None = None,
        violation_recall_types: list[str] | None = None,
        violation_keywords: list[str] | None = None,
        violation_action: str | None = None,
        violation_mute_duration: int | None = None,
        warning_thresholds: list[dict] | None = None,
    ):
        # Group switch
        self.enable = enable if enable is not None else False
        # Join answer
        self.answer = answer if answer is not None else ""
        # Join level
        self.level = level if level is not None else -1
        # Join notify switch
        self.notify_enable = notify_enable if notify_enable is not None else False
        # Join notify content
        self.notify_content = notify_content if notify_content is not None else ""

        # Blacklist enabled
        self.blacklist_enabled = (
            blacklist_enabled if blacklist_enabled is not None else False
        )
        # Blacklist scope: "global" or "group"
        self.blacklist_scope = (
            blacklist_scope if blacklist_scope is not None else "group"
        )
        # Violation recall enabled
        self.violation_recall_enabled = (
            violation_recall_enabled if violation_recall_enabled is not None else False
        )
        # Violation recall types
        self.violation_recall_types = (
            violation_recall_types if violation_recall_types is not None else []
        )
        # Violation keywords list
        self.violation_keywords = (
            violation_keywords if violation_keywords is not None else []
        )
        # Violation action
        self.violation_action = (
            violation_action if violation_action is not None else ACTION_WARN
        )
        # Violation mute duration in seconds
        self.violation_mute_duration = (
            violation_mute_duration if violation_mute_duration is not None else 60
        )
        # Warning thresholds: [{"count": int, "action": str, "mute_duration": int}]
        self.warning_thresholds = (
            warning_thresholds if warning_thresholds is not None else []
        )


class GroupManagerApi:
    def __init__(self, plugin):
        from data.plugins.astrbot_plugin_group_manager.main import GMPlugin

        if isinstance(plugin, GMPlugin):
            self.plugin = plugin

    async def groups(self):
        """Get group list."""
        platforms = await self.platforms()
        groups: list[dict] = []
        for platform in platforms:
            platform_groups = await platform.bot.api.get_group_list()
            for group in platform_groups:
                groups.append(
                    {
                        "id": group["group_id"],
                        "name": group["group_name"],
                        "max": group.get("max_member_count", 0),
                        "now": group.get("member_count", 0),
                    }
                )
        return json_response(groups)

    async def get_setting(self):
        """Get group setting."""
        group_id = request.query.get("id", "", str)

        if len(group_id) < 1:
            return json_response({"code": -1})

        return json_response(
            {
                "c": 0,
                "d": (await self.load_setting(group_id)).__dict__,
            }
        )

    async def load_setting(self, group_id: str) -> GroupSetting:
        enable = await self.plugin.get_kv_data(f"{group_id}_enable", False)
        answer = await self.plugin.get_kv_data(f"{group_id}_answer", "")
        level = await self.plugin.get_kv_data(f"{group_id}_level", -1)
        notify_enable = await self.plugin.get_kv_data(
            f"{group_id}_notify_enable", False
        )
        notify_content = await self.plugin.get_kv_data(
            f"{group_id}_notify_content",
            "Welcome $user_name($user_id) to this group!",
        )
        blacklist_enabled = await self.plugin.get_kv_data(
            f"{group_id}_blacklist_enabled", False
        )
        blacklist_scope = await self.plugin.get_kv_data(
            f"{group_id}_blacklist_scope", "group"
        )
        violation_recall_enabled = await self.plugin.get_kv_data(
            f"{group_id}_violation_recall_enabled", False
        )
        violation_recall_types = await self.plugin.get_kv_data(
            f"{group_id}_violation_recall_types", []
        )
        violation_keywords = await self.plugin.get_kv_data(
            f"{group_id}_violation_keywords", []
        )
        violation_action = await self.plugin.get_kv_data(
            f"{group_id}_violation_action", ACTION_WARN
        )
        violation_mute_duration = await self.plugin.get_kv_data(
            f"{group_id}_violation_mute_duration", 60
        )
        warning_thresholds = await self.plugin.get_kv_data(
            f"{group_id}_warning_thresholds", []
        )

        return GroupSetting(
            enable,
            answer,
            level,
            notify_enable,
            notify_content,
            blacklist_enabled,
            blacklist_scope,
            violation_recall_enabled,
            violation_recall_types,
            violation_keywords,
            violation_action,
            violation_mute_duration,
            warning_thresholds,
        )

    async def has_setting(self):
        """Check if group setting exists."""
        group_id = request.query.get("id", "", str)
        if group_id == "":
            return json_response({"c": -1, "d": {}})

        enable = await self.plugin.get_kv_data(f"{group_id}_enable", None)
        if enable is None:
            return json_response({"c": 2, "d": {}})

        return json_response({"c": 1, "d": {}})

    async def save_setting(self):
        """Save group setting."""
        payload = await request.json(default={})
        if payload is None:
            return json_response({"c": -1, "d": {}})
        group_id = payload.get("id", -1)
        if group_id == -1:
            return json_response({"c": -1, "d": {}})
        enable = payload.get("enable") or False
        answer = payload.get("answer", "")
        level = payload.get("level", -1)
        notify_enable = payload.get("notify_enable", False)
        notify_content = payload.get("notify_content", "")
        blacklist_enabled = payload.get("blacklist_enabled", False)
        blacklist_scope = payload.get("blacklist_scope", "group")
        violation_recall_enabled = payload.get("violation_recall_enabled", False)
        violation_recall_types = payload.get("violation_recall_types", [])
        violation_keywords = payload.get("violation_keywords", [])
        violation_action = payload.get("violation_action", ACTION_WARN)
        violation_mute_duration = payload.get("violation_mute_duration", 60)
        warning_thresholds = payload.get("warning_thresholds", [])

        await self.plugin.put_kv_data(f"{group_id}_enable", enable)
        await self.plugin.put_kv_data(f"{group_id}_answer", answer)
        await self.plugin.put_kv_data(f"{group_id}_level", level)
        await self.plugin.put_kv_data(f"{group_id}_notify_enable", notify_enable)
        await self.plugin.put_kv_data(f"{group_id}_notify_content", notify_content)
        await self.plugin.put_kv_data(
            f"{group_id}_blacklist_enabled", blacklist_enabled
        )
        await self.plugin.put_kv_data(f"{group_id}_blacklist_scope", blacklist_scope)
        await self.plugin.put_kv_data(
            f"{group_id}_violation_recall_enabled", violation_recall_enabled
        )
        await self.plugin.put_kv_data(
            f"{group_id}_violation_recall_types", violation_recall_types
        )
        await self.plugin.put_kv_data(
            f"{group_id}_violation_keywords", violation_keywords
        )
        await self.plugin.put_kv_data(f"{group_id}_violation_action", violation_action)
        await self.plugin.put_kv_data(
            f"{group_id}_violation_mute_duration", violation_mute_duration
        )
        await self.plugin.put_kv_data(
            f"{group_id}_warning_thresholds", warning_thresholds
        )

        return json_response(
            {
                "c": 0,
                "d": (await self.load_setting(group_id)).__dict__,
            }
        )

    # --- Blacklist API ---

    async def load_global_blacklist(self) -> list[str]:
        """Load the global blacklist user ID list."""
        result = await self.plugin.get_kv_data("blacklist_global", [])
        return result if isinstance(result, list) else []

    async def save_global_blacklist(self, blacklist: list[str]) -> None:
        """Save the global blacklist user ID list."""
        await self.plugin.put_kv_data("blacklist_global", blacklist)

    async def load_group_blacklist(self, group_id: str) -> list[str]:
        """Load the per-group blacklist user ID list."""
        result = await self.plugin.get_kv_data(f"{group_id}_blacklist", [])
        return result if isinstance(result, list) else []

    async def save_group_blacklist(self, group_id: str, blacklist: list[str]) -> None:
        """Save the per-group blacklist user ID list."""
        await self.plugin.put_kv_data(f"{group_id}_blacklist", blacklist)

    async def get_global_blacklist(self):
        """API: GET global blacklist."""
        blacklist = await self.load_global_blacklist()
        return json_response({"c": 0, "d": {"list": blacklist}})

    async def save_global_blacklist_api(self):
        """API: POST save global blacklist."""
        payload = await request.json(default={})
        if payload is None:
            return json_response({"c": -1, "d": {}})
        blacklist = payload.get("list", [])
        await self.save_global_blacklist(blacklist)
        return json_response({"c": 0, "d": {}})

    async def get_group_blacklist(self):
        """API: GET group blacklist."""
        group_id = request.query.get("id", "", str)
        if group_id == "":
            return json_response({"c": -1, "d": {}})
        blacklist = await self.load_group_blacklist(group_id)
        return json_response({"c": 0, "d": {"list": blacklist}})

    async def save_group_blacklist_api(self):
        """API: POST save group blacklist."""
        payload = await request.json(default={})
        if payload is None:
            return json_response({"c": -1, "d": {}})
        group_id = payload.get("id", "")
        if group_id == "":
            return json_response({"c": -1, "d": {}})
        blacklist = payload.get("list", [])
        await self.save_group_blacklist(group_id, blacklist)
        return json_response({"c": 0, "d": {}})

    # --- Platforms ---

    async def platforms(self):
        ctx = self.plugin.context
        platforms = ctx.platform_manager.get_insts()
        finds: list[AiocqhttpAdapter] = []
        for platform in platforms:
            if isinstance(platform, AiocqhttpAdapter):
                finds.append(platform)
        return finds
