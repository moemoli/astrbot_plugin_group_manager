from aiocqhttp import MessageSegment
from astrbot.api import logger  # 使用 astrbot 提供的 logger 接口
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from data.plugins.astrbot_plugin_group_manager.platform.base import PlatformBase


class PlatformOneBot(PlatformBase):
    """OneBot平台适配器"""

    async def handle_join_request(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message
        if isinstance(raw, dict):
            post_type = raw.get("post_type", "")
            if post_type == "request":
                group_id = raw.get("group_id")
                if group_id is None:
                    return
                if isinstance(event, AiocqhttpMessageEvent):
                    user_id = str(raw.get("user_id") or "")
                    flag = str(raw.get("flag") or "")
                    sub_type = str(raw.get("sub_type") or "")
                    if sub_type == "invite":
                        # 邀请bot进群
                        if await self.is_astr_admin(user_id):
                            await event.bot.set_group_add_request(
                                flag=flag, sub_type=sub_type, approve=True
                            )
                            await event.bot.send_private_msg(
                                user_id=int(user_id),
                                message=MessageSegment.text(
                                    f"已自动同意加入 群 {group_id} 的邀请。"
                                ),
                            )
                    else:
                        if await self.is_join_enable(group_id):
                            logger.info(
                                f"Received join request for group {group_id}: {raw}"
                            )

                            comment = str(raw.get("comment") or "")
                            comment = comment[
                                comment.find("答案：") + len("答案：") :
                            ]  # 截断备注内容，防止过长
                            info = await event.bot.get_stranger_info(
                                user_id=int(user_id)
                            )
                            level = info["qqLevel"] or 0

                            can_approve, reason = await self.can_approve(
                                comment=comment,
                                group_id=group_id,
                                level=level,
                                user_id=user_id,
                            )
                            logger.info(
                                f"Approval result for user {user_id} in group {group_id}: can_approve={can_approve}, reason={reason}, comment={comment}"
                            )
                            if can_approve:
                                await event.bot.set_group_add_request(
                                    flag=flag, sub_type=sub_type, approve=True
                                )
                                await event.bot.send_group_msg(
                                    group_id=group_id,
                                    message=MessageSegment.text(
                                        f"用户 {info['nickname']}({user_id})  通过审核，已自动同意加群。"
                                    ),
                                )
                            else:
                                if await self.can_reject(group_id):
                                    await event.bot.set_group_add_request(
                                        flag=flag, sub_type=sub_type, approve=False
                                    )
                                    msg = f"用户 {info['nickname']}({user_id})  未通过审核，已自动拒绝加群。\n原因: {reason}\n请求内容: {comment}"
                                else:
                                    msg = f"用户 {info['nickname']}({user_id})  未通过审核，请手动审核。\n原因: {reason}\n请求内容: {comment}"
                                await event.bot.send_group_msg(
                                    group_id=group_id,
                                    message=MessageSegment.text(msg),
                                )
