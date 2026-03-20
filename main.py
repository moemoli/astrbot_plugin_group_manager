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
from .platform.onebot import PlatformOneBot


class GMPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.astr_config = context.get_config()
        self.platform_onebot = PlatformOneBot(self)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
    
    # 判断是否可以调用指令
    async def can_invoke(self, event:AstrMessageEvent) -> bool:
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        # 用户是否为astrbot 管理员
        is_admin = event.is_admin()
         # 可否管理员/群主调用
        can_admin  = await self.get_kv_data(f"{group_id}_can_admin", False) or False
        # 获取astrbot管理员列表
        admin_list = self.astr_config.get("admin_list", [])
        logger.info(f"Checking permissions for user {user_id} in group {group_id}: is_admin={is_admin}, can_admin={can_admin}, admin_list={admin_list}")
        return user_id in admin_list or (is_admin and can_admin)

    # gm指令组
    # 用法: /gm
    @filter.command_group("gm", aliases=["群管"])
    def gm(self):
        pass
    
    
    # 群黑名单配置指令 - 加入黑名单
    # 用法: /gm black @用户/用户id [原因]
    @gm.command("black", aliases=["黑","黑名单","拉黑"])
    async def gm_black(self, event: AstrMessageEvent,userid:str| None , reason: str | None):
        """群黑名单配置指令
        Args:
            userid(str): 用户id或@用户
            reason(str): 黑名单原因
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return
        
        user_id = None
        if isinstance(userid, int):
            user_id = str(userid)
        else:
            for msg in event.message_obj.message:
                if isinstance(msg,At):
                    if msg.qq != "all" and msg.qq != event.get_self_id():
                        user_id = str(msg.qq)
                        break
        if user_id is None:
            yield event.plain_result("指令用法: /gm black @用户/用户id [原因]")
            return
        group_id = event.get_group_id()
        black_list = str(await self.get_kv_data(f"{group_id}_blacklist", "")).split(",")
        black_list.append(f"{user_id};{reason}")
        await self.put_kv_data(f"{group_id}_blacklist", ",".join(set(black_list)))
        yield event.plain_result(f"已经将用户加入黑名单: {user_id}")
    
    # 群黑名单配置指令 - 删除黑名单
    # 用法: /gm delblack @用户/用户id
    @gm.command("delblack", aliases=["删黑","移出黑名单","删除黑名单"])
    async def gm_delblack(self, event: AstrMessageEvent,userid:str| None):
        """群黑名单配置指令
        Args:
            userid(str): 用户id或@用户
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return
        
        user_id = None
        if isinstance(userid, int):
            user_id = str(userid)
        else:
            for msg in event.message_obj.message:
                if isinstance(msg,At):
                    if msg.qq != "all" and msg.qq != event.get_self_id():
                        user_id = str(msg.qq)
                        break
        if user_id is None:
            yield event.plain_result("指令用法: /gm delblack @用户/用户id")
            return
        group_id = event.get_group_id()
        black_list = str(await self.get_kv_data(f"{group_id}_blacklist", "")).split(",")
        for black in black_list:
            if black.startswith(f"{user_id}"):
                black_list.remove(black)
        await self.put_kv_data(f"{group_id}_blacklist", ",".join(set(black_list)))
        yield event.plain_result(f"已经将用户移出黑名单: {user_id}")
        


    ################################################################
    # 入群配置指令组
    # 用法: /gm join
    @gm.group("join", aliases=["入群","加群"])
    def gmjoin(self):
        """入群批准配置指令"""
        pass
    
    # 入群批准配置指令 - 开关
    # 用法: /gm join enable true/1/yes/on/开/开启/enable/启用
    @gmjoin.command("enable", aliases=["switch","status","开关","状态","开","on","启用"])
    async def join_enable(self, event: AstrMessageEvent, enable: str | None):
        """入群批准配置指令 - 开关
        Args:
            enable(str): 开关状态
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return
        group_id = event.get_group_id()
        if enable is None:
            # 空则从消息取状态
            status = "开" in event.get_message_str() or "on" in event.get_message_str() or "启用" in event.get_message_str()
        elif enable.lower() in ["true", "1", "yes", "on","开","开启","enable","启用"]:
            status = True
        else:
            status = False
        await self.put_kv_data(f"{group_id}_join_enable", status)
        if status:
            yield event.plain_result(f"已开启入群批准")
        else:
            yield event.plain_result(f"已关闭入群批准")

    # 入群批准配置指令 - 等级
    # 用法: /gm join level 等级
    @gmjoin.command("level", aliases=["grade","rank","等级","级别"])
    async def join_level(self, event: AstrMessageEvent, level: int | None):
        """入群批准配置指令 - 等级
        Args:
            level(int): 等级
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return
        if level is None:
            yield event.plain_result("指令用法: /gm join level <等级>")
            return
        group_id = event.get_group_id()
        await self.put_kv_data(f"{group_id}_join_level", level)
        yield event.plain_result(f"已经设置入群等级为: {level}")
        
    
    # 入群批准配置指令 - GitHub
    # 用法: /gm join github github仓库
    @gmjoin.command("github", aliases=["gh",])
    async def join_github(self, event: AstrMessageEvent, repo: str | None):
        """入群批准配置指令 - GitHub
        用户入群需要在入群时备注当前配置GitHub仓库的最新提交hash,最少7位
        Args:
            repo(str): GitHub仓库地址
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return
        group_id = event.get_group_id()
        if repo is None:
            await self.delete_kv_data(f"{group_id}_join_github")
            yield event.plain_result("已删除入群GitHub仓库配置")
            return
        
        await self.put_kv_data(f"{group_id}_join_github", repo)
        yield event.plain_result(f"已经设置入群GitHub仓库为: {repo}")
        
    # 入群批准配置指令 - 自动拒绝
    # 用法: /gm join reject true/1/yes/on/开/开启/enable/启用
    @gmjoin.command("reject", aliases=["拒绝","自动拒绝"])
    async def join_reject(self, event: AstrMessageEvent, enable: str | None):
        """入群批准配置指令 - 自动拒绝
        Args:
            enable(str): 开关状态
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return
        group_id = event.get_group_id()
        if enable is None:
            # 空则从消息取状态
            yield event.plain_result("指令用法: /gm join reject <true/1/yes/on/开/开启/enable/启用>")
            return
        elif enable.lower() in ["true", "1", "yes", "on","开","开启","enable","启用"]:
            status = True
        else:
            status = False
        await self.put_kv_data(f"{group_id}_join_reject", status)
        if status:
            yield event.plain_result(f"已开启自动拒绝入群")
        else:
            yield event.plain_result(f"已关闭自动拒绝入群")
    

    ################################################################
    # 入群备注配置指令组
    # 用法: /gm join comment
    @gmjoin.group("comment")
    def gmjoincomment(self):
        """入群批准备注配置指令"""
        pass
    
    # 入群备注配置指令组 - 黑名单
    # 用法: /gm join comment black 黑名单词汇1,词汇2;词汇3/词汇4:词汇5. 词汇6
    @gmjoincomment.command("black", aliases=["block","ban","黑","屏蔽","禁止","黑名单"])
    async def comment_black(self, event: AstrMessageEvent, comment: GreedyStr):
        """入群批准配置指令 - 备注 - 黑名单
        Args:
            comment(GreedyStr): 备注黑名单词汇
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return

        group_id = event.get_group_id()
        src_list = str(await self.get_kv_data(f"{group_id}_join_comment_black", "")).split(",")
        black_list = list[str]()
        black_list.extend(comment.split(","))
        black_list.extend(comment.split(";"))
        black_list.extend(comment.split("/"))
        black_list.extend(comment.split(":"))
        black_list.extend(comment.split("."))
        black_list.extend(comment.split(" "))
        black_list.extend(src_list)
        black_list = ",".join(set(black_list))
        await self.put_kv_data(f"{group_id}_join_comment_black", black_list)
        yield event.plain_result(f"已经添加入群备注黑名单: {black_list}")
    
    # 入群备注配置指令组 - 删除黑名单
    # 用法: /gm join comment delblack 黑名单词汇1,词汇2;词汇3/词汇4:词汇5. 词汇6
    @gmjoincomment.command("delblack", aliases=["deleteblack","removeblack","删黑","删除黑名单"])
    async def comment_delblack(self, event: AstrMessageEvent, comment: GreedyStr):
        """入群批准配置指令 - 备注 - 删除黑名单
        Args:
            comment(GreedyStr): 备注黑名单词汇
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return

        group_id = event.get_group_id()
        src_list = str(await self.get_kv_data(f"{group_id}_join_comment_black", "")).split(",")
        black_list = list[str]()
        black_list.extend(comment.split(","))
        black_list.extend(comment.split(";"))
        black_list.extend(comment.split("/"))
        black_list.extend(comment.split(":"))
        black_list.extend(comment.split("."))
        black_list.extend(comment.split(" "))
        black_list = set(black_list)
        for black in black_list:
            if black in src_list:
                src_list.remove(black)
                
        await self.put_kv_data(f"{group_id}_join_comment_black", ",".join(src_list))
        yield event.plain_result(f"已经删除入群备注黑名单: {black_list}")
    
    # 入群事件处理器，分平台处理
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_join_request(self, event: AstrMessageEvent):
        """处理入群请求事件"""
        if event.get_message_type() != MessageType.OTHER_MESSAGE:
            return
        if isinstance(event, AiocqhttpMessageEvent):
            await self.platform_onebot.handle_join_request(event)
        else:
            logger.warning(f"收到不支持的平台的入群特殊事件: {event.platform.name}")
    
    ################################################################
    # 全局配置指令组
    # 仅astrbot管理员可用
    # 用法: /gm global
    @gm.group("global", aliases=["全局"])
    @filter.permission_type(filter.PermissionType.ADMIN)
    def gmglobal(self):
        pass
    
    
    # 全局黑名单配置指令 - 加入黑名单
    # 仅astrbot管理员可用
    # 用法: /gm global black @用户/用户id [原因]
    @gmglobal.command("black", aliases=["黑","黑名单","拉黑"])
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def global_black(self, event: AstrMessageEvent,userid:str| None , reason: str | None):
        """全局黑名单配置指令
        Args:
            userid(str): 用户id或@用户
            reason(str): 黑名单原因
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return
        
        user_id = None
        if isinstance(userid, int):
            user_id = str(userid)
        else:
            for msg in event.message_obj.message:
                if isinstance(msg,At):
                    if msg.qq != "all" and msg.qq != event.get_self_id():
                        user_id = str(msg.qq)
                        break
        if user_id is None:
            yield event.plain_result("指令用法: /gm global black @用户/用户id [原因]")
            return
        black_list = str(await self.get_kv_data(f"global_blacklist", "")).split(",")
        black_list.append(f"{user_id};{reason}")
        await self.put_kv_data(f"global_blacklist", ",".join(set(black_list)))
        yield event.plain_result(f"已经将用户加入黑名单: {user_id}")
    
    # 全局黑名单配置指令 - 删除黑名单
    # 仅astrbot管理员可用
    # 用法: /gm global delblack @用户/用户id
    @gmglobal.command("delblack", aliases=["删黑","移出黑名单","删除黑名单"])
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def global_delblack(self, event: AstrMessageEvent,userid:str| None):
        """全局黑名单配置指令
        Args:
            userid(str): 用户id或@用户
        """
        if not await self.can_invoke(event):
            yield event.plain_result("你没有权限使用这个指令哦")
            return
        
        user_id = None
        if isinstance(userid, int):
            user_id = str(userid)
        else:
            for msg in event.message_obj.message:
                if isinstance(msg,At):
                    if msg.qq != "all" and msg.qq != event.get_self_id():
                        user_id = str(msg.qq)
                        break
        if user_id is None:
            yield event.plain_result("指令用法: /gm global delblack @用户/用户id")
            return
        black_list = str(await self.get_kv_data(f"global_blacklist", "")).split(",")
        for black in black_list:
            if black.startswith(f"{user_id}"):
                black_list.remove(black)
        await self.put_kv_data(f"global_blacklist", ",".join(set(black_list)))
        yield event.plain_result(f"已经将用户移出黑名单: {user_id}")
        
