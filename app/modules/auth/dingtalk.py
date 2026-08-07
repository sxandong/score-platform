"""钉钉扫码登录服务"""
import re
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import httpx
from pypinyin import lazy_pinyin

from app.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, hash_password
)
from app.core.exceptions import ValidationException
from app.models.user import User, Role

logger = logging.getLogger(__name__)


def _name_to_pinyin(real_name: str) -> str:
    """将中文姓名转为拼音用户名"""
    py_list = lazy_pinyin(real_name)
    username = ''.join(py_list).lower()
    username = re.sub(r'[^a-z0-9]', '', username)
    return username or f"user_{abs(hash(real_name)) % 10000}"


async def _get_existing_user_or_create(
    db: AsyncSession, union_id: str, name: str
) -> User:
    """根据钉钉union_id查找或创建用户

    匹配顺序：
    1. 通过 union_id 匹配（已绑定钉钉的用户）→ 直接登录
    2. 通过 real_name 匹配（管理员手动创建的同名用户）→ 关联union_id后登录
    3. 都没匹配到 → 创建新用户（teacher角色，默认密码123456）
    """
    # 1. 通过 union_id 查找已绑定用户
    result = await db.execute(
        select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.dingtalk_union_id == union_id)
    )
    user = result.scalar_one_or_none()

    # 2. 未绑定union_id，尝试通过姓名匹配已有用户
    if not user and name:
        result = await db.execute(
            select(User).options(
                selectinload(User.roles).selectinload(Role.permissions)
            ).where(
                User.real_name == name,
                (User.dingtalk_union_id == None) | (User.dingtalk_union_id == "")
            ).limit(1)
        )
        user = result.scalar_one_or_none()
        if user:
            # 关联钉钉账号
            user.dingtalk_union_id = union_id
            await db.commit()
            await db.refresh(user)
            logger.info("用户 %s 已关联钉钉账号", user.username)

    if user:
        if user.status != "active":
            raise ValidationException("用户已禁用")
        if user.roles:
            return user
        # 已有用户但无角色，补发teacher角色
        teacher_role = await _ensure_teacher_role(db)
        user.roles.append(teacher_role)
        await db.commit()
        await db.refresh(user)
        return user

    # 新用户：生成唯一用户名
    username = await _generate_unique_username(db, name)
    default_password = hash_password("123456")

    teacher_role = await _ensure_teacher_role(db)
    new_user = User(
        username=username,
        password_hash=default_password,
        real_name=name,
        dingtalk_union_id=union_id,
        status="active",
        must_change_password=True,
    )
    new_user.roles.append(teacher_role)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def _ensure_teacher_role(db: AsyncSession) -> Role:
    """确保teacher角色存在"""
    result = await db.execute(
        select(Role).where(Role.code == "teacher")
    )
    role = result.scalar_one_or_none()
    if role:
        return role
    role = Role(name="教师", code="teacher", description="教师角色")
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def _generate_unique_username(db: AsyncSession, name: str) -> str:
    """生成唯一用户名（拼音+冲突后缀）"""
    base = _name_to_pinyin(name)
    username = base
    counter = 2
    while True:
        result = await db.execute(
            select(User.id).where(User.username == username).limit(1)
        )
        if result.scalar_one_or_none() is None:
            return username
        username = f"{base}{counter}"
        counter += 1


_cached_corp_id: str | None = None


async def _get_corp_access_token(client: httpx.AsyncClient) -> str:
    """获取企业内部应用 accessToken"""
    token_url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    token_resp = await client.post(token_url, json={
        "appKey": settings.DINGTALK_APP_KEY,
        "appSecret": settings.DINGTALK_APP_SECRET,
    })
    token_data = token_resp.json()
    if "accessToken" not in token_data:
        logger.error("获取企业accessToken失败: %s", token_data)
        raise ValidationException("钉钉配置异常")
    return token_data["accessToken"]


async def _check_user_in_corp(client: httpx.AsyncClient, union_id: str) -> bool:
    """校验用户是否属于本企业

    通过企业内部应用accessToken + unionId 查询用户 userid，
    如果用户不属于本企业，接口会返回错误。
    权限不足时跳过校验（允许登录），避免误拒本单位员工。
    """
    try:
        corp_access_token = await _get_corp_access_token(client)
        # 通过 unionId 获取 userid（仅本企业用户能查到）
        resp = await client.post(
            "https://oapi.dingtalk.com/topapi/user/getbyunionid",
            params={"access_token": corp_access_token},
            json={"unionid": union_id},
        )
        data = resp.json()
        errcode = data.get("errcode", 0)
        if errcode == 0:
            return True  # 用户存在
        # 60121: 用户不存在于本企业 → 拒绝
        if errcode == 60121 or data.get("sub_code") == "60121":
            logger.warning("用户不属于本企业: union_id=%s", union_id)
            return False
        # 权限不足（88/60011）或其他错误 → 跳过校验，允许登录
        logger.warning("企业校验跳过（权限不足或接口异常）: errcode=%s, msg=%s", errcode, data.get("errmsg", ""))
        return True
    except Exception as e:
        logger.error("校验用户企业归属失败，跳过校验: %s", e)
        return True


async def exchange_code_for_user(auth_code: str) -> dict:
    """用钉钉新版OAuth2的authCode换取用户信息

    流程：
    1. 用 authCode 换取用户 accessToken
    2. 用用户 accessToken 获取用户个人信息（unionId等）
    3. 用企业 accessToken + unionId 校验用户是否属于本企业
    """
    if not settings.DINGTALK_APP_KEY or not settings.DINGTALK_APP_SECRET:
        raise ValidationException("钉钉登录未配置")

    async with httpx.AsyncClient(timeout=15) as client:
        # 1. 用 authCode 换取用户 accessToken
        token_url = "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
        token_resp = await client.post(token_url, json={
            "clientId": settings.DINGTALK_APP_KEY,
            "clientSecret": settings.DINGTALK_APP_SECRET,
            "code": auth_code,
            "grantType": "authorization_code",
        })
        token_data = token_resp.json()
        if "accessToken" not in token_data:
            logger.error("获取钉钉用户accessToken失败: %s", token_data)
            msg = token_data.get("message") or token_data.get("errmsg") or "获取token失败"
            raise ValidationException(f"钉钉登录失败: {msg}")
        user_access_token = token_data["accessToken"]

        # 2. 获取用户通讯录个人信息
        userinfo_url = "https://api.dingtalk.com/v1.0/contact/users/me"
        info_resp = await client.get(userinfo_url, headers={
            "x-acs-dingtalk-access-token": user_access_token,
        })
        info_data = info_resp.json()
        union_id = info_data.get("unionId")
        if not union_id:
            logger.error("获取钉钉用户信息失败: %s", info_data)
            msg = info_data.get("message") or "获取用户信息失败"
            raise ValidationException(f"钉钉登录失败: {msg}")

        # 3. 校验用户是否属于本企业
        is_in_corp = await _check_user_in_corp(client, union_id)
        if not is_in_corp:
            raise ValidationException("非本单位用户，禁止登录")

        return {
            "unionid": union_id,
            "userid": info_data.get("openId", ""),
            "name": info_data.get("nick") or "钉钉用户",
            "avatar": info_data.get("avatarUrl") or "",
        }


async def dingtalk_login(db: AsyncSession, auth_code: str) -> dict:
    """钉钉扫码登录主流程"""
    user_info = await exchange_code_for_user(auth_code)
    union_id = user_info["unionid"]
    name = user_info["name"]

    user = await _get_existing_user_or_create(db, union_id, name)

    role_codes = user.role_codes
    permission_codes: list[str] = []
    for role in user.roles:
        permission_codes.extend(role.permission_codes)
    permission_codes = sorted(set(permission_codes))

    return {
        "access_token": create_access_token(user.id, role_codes),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "roles": role_codes,
            "permissions": permission_codes,
            "must_change_password": user.must_change_password or False,
        },
    }
