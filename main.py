from aiocqhttp import MessageSegment
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import At, ComponentType, Reply
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.core.star.filter.command import GreedyStr
from data.plugins.astrbot_plugin_group_manager.api.settings import GroupManagerApi

PLUGIN_NAME = "astrbot_plugin_group_manager"


class GMPlugin(Star):

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.astr_config = context.get_config()
        self.api = GroupManagerApi(self)
        self.approve_friend = self.config.get("auto_approve_friend", False)
        self.approve_group = self.config.get("auto_approve_group", False)

        # 群查询接口
        context.register_web_api(
            f"/{PLUGIN_NAME}/groups",
            self.api.groups,
            ["GET"],
            "List groups",
        )

        # 群设置查询接口
        context.register_web_api(
            f"/{PLUGIN_NAME}/settings/load",
            self.api.get_setting,
            ["GET"],
            "Get group settings",
        )

        # 群设置保存接口
        context.register_web_api(
            f"/{PLUGIN_NAME}/settings/save",
            self.api.save_setting,
            ["POST"],
            "Save group settings",
        )

        # 群设置存在性检查接口
        context.register_web_api(
            f"/{PLUGIN_NAME}/settings/has",
            self.api.has_setting,
            ["GET"],
            "Check if group settings exist",
        )

    async def is_astr_admin(self, user_id: str) -> bool:
        admin_list = self.astr_config.get("admins_id", [])
        return user_id in admin_list

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def recall_aiocqhttp(self, event: AstrMessageEvent):

        msg = event.message_str
        if len(msg) < 1:
            return
        # 处理群消息并撤回

        # 终止事件传播
        event.stop_event()

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def handle_aiocqhttp(self, event: AiocqhttpMessageEvent):
        """处理来自 aiocqhttp 平台的消息事件"""
        raw = event.message_obj.raw_message
        if not isinstance(raw, dict):
            # 不是目标类型，跳过
            return
        post_type = raw.get("post_type")
        if post_type != "request":
            # 不是请求类事件，返回
            return
        request_type = raw.get("request_type")
        flag = raw.get("flag")
        if request_type != "group":
            # 如果设置了自动同意好友，同意
            if self.approve_friend:
                await event.bot.api.set_friend_add_request(flag=str(flag), approve=True)
                return
        sub_type = raw.get("sub_type")
        user_id = raw.get("user_id")
        if sub_type != "add":
            if self.approve_group or await self.is_astr_admin(str(user_id)):
                # 如果设置了自动同意入群邀请，或是管理员邀请，同意
                await event.bot.api.set_group_add_request(
                    flag=str(flag), sub_type=str(sub_type), approve=True
                )
            return
        # 开始根据分群配置处理加群请求
        group_id = raw.get("group_id")
        setting = await self.api.load_setting(str(group_id))
        if not setting.enable:
            # 如果群管未启用，直接返回
            return
        comment = str(raw.get("comment") or "")
        comment = comment[
            comment.find("答案：") + len("答案：") :
        ]  # 截断备注内容，防止过长
        info = await event.bot.get_stranger_info(user_id=int(str(user_id)))
        level = info.get("level", 0)
        if (setting.answer not in comment) or (level < setting.level):
            # 如果答案不正确，或等级不够，拒绝入群
            await event.bot.api.set_group_add_request(
                flag=str(flag), sub_type=str(sub_type), approve=False
            )
            return
        await event.bot.api.set_group_add_request(
            flag=str(flag), sub_type=str(sub_type), approve=True
        )
        if setting.notify_enable:
            # 如果启用了入群通知，发送入群通知
            notify_content = setting.notify_content.replace(
                "$user_name", str(raw.get("user_name") or "")
            ).replace("$user_id", str(user_id))
            await event.bot.api.send_group_msg(
                group_id=int(str(group_id)),
                message=MessageSegment.text(notify_content),
            )
        # 终止事件传播
        event.stop_event()
