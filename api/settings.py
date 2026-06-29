from astrbot.api.web import json_response, request
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_platform_adapter import (
    AiocqhttpAdapter,
)
from astrbot.core.star.filter.platform_adapter_type import PlatformAdapterType


class GroupSetting:
    def __init__(
        self,
        enable: bool | None,
        answer: str | None,
        level: int | None,
        notify_enable: bool | None,
        notify_content: str | None,
    ):
        if enable is None:
            enable = False
        if answer is None:
            answer = ""
        if level is None:
            level = -1
        if notify_enable is None:
            notify_enable = False
        if notify_content is None:
            notify_content = ""
        # 群管开关
        self.enable = enable
        # 入群答案
        self.answer = answer
        # 入群等级
        self.level = level
        # 入群通知开关
        self.notify_enable = notify_enable
        # 入群通知内容
        self.notify_content = notify_content


class GroupManagerApi:
    def __init__(self, plugin):
        from data.plugins.astrbot_plugin_group_manager.main import GMPlugin

        if isinstance(plugin, GMPlugin):
            self.plugin = plugin

    async def groups(self):
        """获取群组列表"""
        # 获取群组列表的逻辑
        platforms = await self.platforms()
        groups: list[dict] = []
        for platform in platforms:
            # 假设每个平台都有一个获取群组列表的方法
            platform_groups = await platform.bot.api.get_group_list()
            for group in platform_groups:
                groups.append({"id": group["group_id"], "name": group["group_name"]})
        return json_response(groups)

    async def get_setting(self):
        """修改群组设置"""

        group_id = request.query.get("id", "", str)

        if len(group_id) < 1:
            return json_response({"code": -1})

        return json_response(
            {
                "code": 0,
                "data": (await self.load_setting(group_id)).__dict__,
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
            f"{group_id}_notify_content", "欢迎 $user_name($user_id) 加入本群！"
        )

        return GroupSetting(enable, answer, level, notify_enable, notify_content)

    async def has_setting(self):
        """判断群组设置"""
        group_id = request.query.get("id", "", str)
        if group_id == "":
            return json_response({"code": -1})

        enable = await self.plugin.get_kv_data(f"{group_id}_enable", None)
        if enable is None:
            return json_response({"code": 2})

        return json_response({"code": 1})

    async def save_setting(self):
        """修改群组设置"""
        payload = await request.json(default={})
        if payload is None:
            return json_response({"code": -1})
        group_id = payload.get("id", -1)
        if group_id == -1:
            return json_response({"code": -1})
        enable = payload.get("enable") or False
        answer = payload.get("answer", "")
        level = payload.get("level", -1)
        notify_enable = payload.get("notify_enable", False)
        notify_content = payload.get("notify_content", "")

        await self.plugin.put_kv_data(f"{group_id}_enable", enable)
        await self.plugin.put_kv_data(f"{group_id}_answer", answer)
        await self.plugin.put_kv_data(f"{group_id}_level", level)
        await self.plugin.put_kv_data(f"{group_id}_notify_enable", notify_enable)
        await self.plugin.put_kv_data(f"{group_id}_notify_content", notify_content)

        return json_response(
            {
                "code": 0,
                "data": (await self.load_setting(group_id)).__dict__,
            }
        )

    async def platforms(self):
        ctx = self.plugin.context
        platforms = ctx.platform_manager.get_insts()
        finds: list[AiocqhttpAdapter] = []
        for platform in platforms:
            if isinstance(platform, AiocqhttpAdapter):
                finds.append(platform)
        return finds
