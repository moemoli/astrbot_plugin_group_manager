# 平台适配基础类

from astrbot.api import logger # 使用 astrbot 提供的 logger 接口
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from data.plugins.astrbot_plugin_group_manager.utils import fetch_url


class PlatformBase:
    def __init__(self, plugin):
        self.plugin = plugin

    async def is_join_enable(self, group_id: str) -> bool:
        """检查入群批准是否开启"""
        return await self.plugin.get_kv_data(f"{group_id}_join_enable", False) or False

    async def is_github_enable(self, group_id: str) -> bool:
        """检查 GitHub 入群是否开启"""
        return await self.get_github_repo(group_id) is not None

    async def get_github_repo(self, group_id: str) -> str | None:
        """获取 GitHub 仓库地址"""
        return await self.plugin.get_kv_data(f"{group_id}_join_github", None)

    async def get_github_repo_lastest_hash(self, group_id: str) -> str | None:
        """获取 GitHub 仓库最新提交哈希"""
        github_token = self.plugin.config.get("github_token")
        github_repo = (
            str(await self.get_github_repo(group_id) or "")
            .replace("https://github.com/", "")
            .replace(".git", "")
        )
        headers = {}
        if github_token == "":
            headers = {"Authorization": f"token {github_token}"}
        logger.info(f"Fetching latest commit hash for GitHub repo {github_repo} with headers: {headers}")
        github_api = f"https://api.github.com/repos/{github_repo}/commits?per_page=1"
        result = await fetch_url(github_api, headers=headers)
        if isinstance(result, dict):
            return result[0]["sha"] or None
        return None

    async def get_join_comment_blacklist(self, group_id: str) -> list[str]:
        """获取入群申请评论黑名单列表"""
        return str(
            await self.plugin.get_kv_data(f"{group_id}_join_comment_black", "") or ""
        ).split(",")
        
    async def get_join_level(self, group_id: str) -> int:
        """获取入群批准难度等级"""
        return await self.plugin.get_kv_data(f"{group_id}_join_level", 0) or 0
    
    async def can_reject(self, group_id: str) -> bool:
        """获取是否自动拒绝"""
        return await self.plugin.get_kv_data(f"{group_id}_join_reject", False) or False
    
    async def get_group_blacklist(self, group_id: str) -> list[str]:
        """获取群黑名单列表"""
        return str(
            await self.plugin.get_kv_data(f"{group_id}_blacklist", "") or ""
        ).split(",")
        
    async def get_global_blacklist(self, group_id: str) -> list[str]:
        """获取全局黑名单列表"""
        return str(
            await self.plugin.get_kv_data(f"global_blacklist", "") or ""
        ).split(",")
        
    async def can_approve(
        self, comment: str, group_id: str, level: int, user_id: str
    ):
        # 全局黑名单检测
        for black in await self.get_global_blacklist(group_id):
            if black.startswith(f"{user_id}"):
                return False, "用户在全局黑名单中"
        # 群黑名单检测
        for black in await self.get_group_blacklist(group_id):
            if black.startswith(f"{user_id}"):
                return False, "用户在黑名单中"
        # GitHub 入群检测
        if await self.is_github_enable(group_id):
            logger.info(f"GitHub join check enabled for group {group_id}, checking comment: {comment}")
            lastest_hash =  await self.get_github_repo_lastest_hash(group_id)
            if (
               not (lastest_hash is not None
                and comment != ""
                and lastest_hash.startswith(comment)
                and level >= await self.get_join_level(group_id))
            ):
                logger.info(f"GitHub join check failed for user {user_id} in group {group_id}: lastest_hash={lastest_hash}, comment={comment}, level={level}, required_level={self.get_join_level(group_id)}")
                return False, "错误的 GitHub 提交哈希，或者入群等级不足"
        # 黑名单备注检测
        for black in await self.get_join_comment_blacklist(group_id):
            if black in comment:
                return False, "备注内容在黑名单中"
        if level < await self.get_join_level(group_id):
            return False, "入群等级不足"
        return True, "入群申请通过"

    def handle_join_request(self, event: AstrMessageEvent):
        """处理入群请求的函数，具体实现由不同平台的适配类完成"""
        raise NotImplementedError("handle_join_request 方法需要在子类中实现")
