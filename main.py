import re

from aiocqhttp import MessageSegment

from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from data.plugins.astrbot_plugin_group_manager.api.settings import (
    ACTION_KICK,
    ACTION_MUTE,
    ACTION_RECALL_KICK,
    ACTION_RECALL_MUTE,
    RECALL_TYPE_CARDS,
    RECALL_TYPE_CHAT_HISTORY,
    RECALL_TYPE_FRIEND_RECOMMEND,
    RECALL_TYPE_GROUP_RECOMMEND,
    RECALL_TYPE_KEYWORDS,
    RECALL_TYPE_LINKS,
    GroupManagerApi,
)

PLUGIN_NAME = "astrbot_plugin_group_manager"

URL_PATTERN = re.compile(r"https?://\S+")


class GMPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.astr_config = context.get_config()
        self.api = GroupManagerApi(self)
        self.approve_friend = self.config.get("auto_approve_friend", False)
        self.approve_group = self.config.get("auto_approve_group", False)

        # Group list API
        context.register_web_api(
            f"/{PLUGIN_NAME}/groups",
            self.api.groups,
            ["GET"],
            "List groups",
        )

        # Group setting load API
        context.register_web_api(
            f"/{PLUGIN_NAME}/settings/load",
            self.api.get_setting,
            ["GET"],
            "Get group settings",
        )

        # Group setting save API
        context.register_web_api(
            f"/{PLUGIN_NAME}/settings/save",
            self.api.save_setting,
            ["POST"],
            "Save group settings",
        )

        # Group setting existence check API
        context.register_web_api(
            f"/{PLUGIN_NAME}/settings/has",
            self.api.has_setting,
            ["GET"],
            "Check if group settings exist",
        )

        # Global blacklist API
        context.register_web_api(
            f"/{PLUGIN_NAME}/blacklist/global",
            self.api.get_global_blacklist,
            ["GET"],
            "Get global blacklist",
        )
        context.register_web_api(
            f"/{PLUGIN_NAME}/blacklist/global/save",
            self.api.save_global_blacklist_api,
            ["POST"],
            "Save global blacklist",
        )

        # Per-group blacklist API
        context.register_web_api(
            f"/{PLUGIN_NAME}/blacklist/group",
            self.api.get_group_blacklist,
            ["GET"],
            "Get group blacklist",
        )
        context.register_web_api(
            f"/{PLUGIN_NAME}/blacklist/group/save",
            self.api.save_group_blacklist_api,
            ["POST"],
            "Save group blacklist",
        )

    async def is_astr_admin(self, user_id: str) -> bool:
        admin_list = self.astr_config.get("admins_id", [])
        return user_id in admin_list

    async def initialize(self):
        """Optional async plugin initialization, called after instantiation."""

    async def terminate(self):
        """Optional async plugin teardown, called on unload/disable."""

    def _extract_text_content(self, segments: list[dict]) -> str:
        """Extract plain text from message segments."""
        parts = []
        for seg in segments:
            if seg.get("type") == "text":
                parts.append(seg.get("data", {}).get("text", ""))
        return " ".join(parts)

    def _match_violation(self, raw: dict, setting) -> bool:
        """Check if a message violates any enabled recall rule.

        Args:
            raw: The raw event dict from aiocqhttp.
            setting: The GroupSetting for this group.

        Returns:
            True if a violation is detected.
        """
        segments = raw.get("message", [])
        text_content = self._extract_text_content(segments)

        for vtype in setting.violation_recall_types:
            if vtype == RECALL_TYPE_KEYWORDS:
                for keyword in setting.violation_keywords:
                    if keyword and keyword in text_content:
                        return True

            elif vtype == RECALL_TYPE_CHAT_HISTORY:
                for seg in segments:
                    if seg.get("type") == "forward":
                        return True

            elif vtype == RECALL_TYPE_LINKS:
                if URL_PATTERN.search(text_content):
                    return True

            elif vtype == RECALL_TYPE_GROUP_RECOMMEND:
                for seg in segments:
                    if seg.get("type") in ("json", "xml"):
                        data_str = str(seg.get("data", {}))
                        if any(kw in data_str for kw in ("\u7fa4", "group", "invite")):
                            return True

            elif vtype == RECALL_TYPE_FRIEND_RECOMMEND:
                for seg in segments:
                    if seg.get("type") in ("json", "xml"):
                        data_str = str(seg.get("data", {}))
                        if any(
                            kw in data_str for kw in ("\u597d\u53cb", "friend", "add")
                        ):
                            return True

            elif vtype == RECALL_TYPE_CARDS:
                for seg in segments:
                    if seg.get("type") in ("json", "xml"):
                        return True

        return False

    def _resolve_action_and_duration(self, warn_count: int, setting) -> tuple[str, int]:
        """Determine the punishment action and mute duration based on thresholds.

        Checks warning thresholds in descending order of count. Falls back to
        the base violation action when no threshold is matched.

        Args:
            warn_count: Current warning count for the user.
            setting: The GroupSetting containing thresholds and base action.

        Returns:
            A tuple of (action_string, mute_duration_seconds).
        """
        sorted_thresholds = sorted(
            setting.warning_thresholds,
            key=lambda t: t.get("count", 0),
            reverse=True,
        )
        for threshold in sorted_thresholds:
            if warn_count >= threshold.get("count", 0):
                action = threshold.get("action", setting.violation_action)
                duration = threshold.get(
                    "mute_duration", setting.violation_mute_duration
                )
                return action, duration

        return setting.violation_action, setting.violation_mute_duration

    async def _apply_punishment(
        self,
        event: AiocqhttpMessageEvent,
        group_id: str,
        user_id: str,
        action: str,
        mute_duration: int,
    ):
        """Execute the punishment action on the user.

        Args:
            event: The message event (provides bot API access).
            group_id: Target group ID.
            user_id: Target user ID.
            action: The action string to execute.
            mute_duration: Mute duration in seconds (used when action involves mute).
        """
        if action in (ACTION_MUTE, ACTION_RECALL_MUTE):
            try:
                await event.bot.api.set_group_ban(
                    group_id=int(group_id),
                    user_id=int(user_id),
                    duration=mute_duration,
                )
                logger.info(
                    f"Muted user {user_id} in group {group_id} for {mute_duration}s"
                )
            except Exception as e:
                logger.warning(f"Failed to mute user {user_id}: {e}")

        elif action in (ACTION_KICK, ACTION_RECALL_KICK):
            try:
                await event.bot.api.set_group_kick(
                    group_id=int(group_id),
                    user_id=int(user_id),
                )
                logger.info(f"Kicked user {user_id} from group {group_id}")
            except Exception as e:
                logger.warning(f"Failed to kick user {user_id}: {e}")

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def recall_aiocqhttp(self, event: AiocqhttpMessageEvent):
        """Handle group messages: detect violations, recall, and punish."""
        raw = event.message_obj.raw_message
        if not isinstance(raw, dict):
            return

        group_id = str(raw.get("group_id", ""))
        user_id = str(raw.get("user_id", ""))
        message_id = raw.get("message_id")

        if not group_id or not user_id or message_id is None:
            return

        setting = await self.api.load_setting(group_id)
        if not setting.violation_recall_enabled:
            return

        if not self._match_violation(raw, setting):
            return

        # Recall the message
        try:
            await event.bot.api.delete_msg(message_id=int(message_id))
            logger.info(
                f"Recalled message {message_id} in group {group_id} from user {user_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to recall message {message_id}: {e}")

        # Track warning count
        warn_key = f"{group_id}_{user_id}_warnings"
        warn_count = await self.get_kv_data(warn_key, 0)
        warn_count += 1
        await self.put_kv_data(warn_key, warn_count)

        # Determine action
        action, mute_duration = self._resolve_action_and_duration(warn_count, setting)

        # Apply punishment
        await self._apply_punishment(event, group_id, user_id, action, mute_duration)

        logger.info(
            f"Violation in group {group_id}: user={user_id}, "
            f"action={action}, warnings={warn_count}"
        )
        event.stop_event()

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def handle_aiocqhttp(self, event: AiocqhttpMessageEvent):
        """Handle events from the aiocqhttp platform."""
        raw = event.message_obj.raw_message
        if not isinstance(raw, dict):
            return
        post_type = raw.get("post_type")
        if post_type != "request":
            return
        request_type = raw.get("request_type")
        flag = raw.get("flag")
        if request_type != "group":
            if self.approve_friend:
                await event.bot.api.set_friend_add_request(flag=str(flag), approve=True)
                return
        sub_type = raw.get("sub_type")
        user_id = raw.get("user_id")
        if sub_type != "add":
            if self.approve_group or await self.is_astr_admin(str(user_id)):
                await event.bot.api.set_group_add_request(
                    flag=str(flag), sub_type=str(sub_type), approve=True
                )
            return

        group_id = raw.get("group_id")
        setting = await self.api.load_setting(str(group_id))
        if not setting.enable:
            return

        # Blacklist check
        if setting.blacklist_enabled:
            if setting.blacklist_scope == "global":
                blacklist = await self.api.load_global_blacklist()
            else:
                blacklist = await self.api.load_group_blacklist(str(group_id))
            if str(user_id) in blacklist:
                logger.info(
                    f"Rejected user {user_id} joining group {group_id}: in blacklist"
                )
                await event.bot.api.set_group_add_request(
                    flag=str(flag), sub_type=str(sub_type), approve=False
                )
                event.stop_event()
                return

        comment = str(raw.get("comment") or "")
        comment = comment[
            comment.find("\u7b54\u6848\uff1a") + len("\u7b54\u6848\uff1a") :
        ]
        info = await event.bot.get_stranger_info(user_id=int(str(user_id)))
        level = info.get("level", 0)
        if (setting.answer not in comment) or (level < setting.level):
            await event.bot.api.set_group_add_request(
                flag=str(flag), sub_type=str(sub_type), approve=False
            )
            return
        await event.bot.api.set_group_add_request(
            flag=str(flag), sub_type=str(sub_type), approve=True
        )
        if setting.notify_enable:
            notify_content = setting.notify_content.replace(
                "$user_name", str(raw.get("user_name") or "")
            ).replace("$user_id", str(user_id))
            await event.bot.api.send_group_msg(
                group_id=int(str(group_id)),
                message=MessageSegment.text(notify_content),
            )
        event.stop_event()
