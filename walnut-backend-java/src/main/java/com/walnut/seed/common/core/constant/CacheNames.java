package com.walnut.seed.common.core.constant;

/**
 * 缓存常量
 * <p>
 * 包含两部分：
 * 1. Redis Key 前缀 — 用于直接操作 Redis 时的 key 前缀
 * 2. Spring Cache 缓存组名称 — 格式为 name#ttl#maxIdleTime#maxSize
 * <p>
 * TTL 说明：
 * ttl 过期时间（0=不过期，默认0）
 * maxIdleTime 最大空闲时间（LRU清理，0=不检测，默认0）
 * maxSize 组最大长度（LRU清理，0=无限长，默认0）
 * <p>
 * 示例：test#60s、test#0#60s、test#0#1m#1000、test#1h#0#500
 *
 * @author deepin_sir
 */
public interface CacheNames {

    // ===================== 全局 Redis Key 前缀 =====================

    /**
     * 全局 redis key 前缀
     */
    String GLOBAL_REDIS_KEY = "global:";

    // ===================== Redis Key 前缀 =====================

    /**
     * 在线用户 redis key
     */
    String ONLINE_TOKEN_KEY = "online_tokens:";

    /**
     * 参数管理 cache key
     */
    String SYS_CONFIG_KEY = "sys_config:";

    /**
     * 字典管理 cache key
     */
    String SYS_DICT_KEY = "sys_dict:";

    /**
     * 登录账户密码错误次数 redis key
     */
    String PWD_ERR_CNT_KEY = "pwd_err_cnt:";

    /**
     * 验证码 redis key
     */
    String CAPTCHA_CODE_KEY = GLOBAL_REDIS_KEY + "captcha_codes:";

    /**
     * 防重提交 redis key
     */
    String REPEAT_SUBMIT_KEY = GLOBAL_REDIS_KEY + "repeat_submit:";

    /**
     * 限流 redis key
     */
    String RATE_LIMIT_KEY = GLOBAL_REDIS_KEY + "rate_limit:";

    /**
     * 三方认证 redis key
     */
    String SOCIAL_AUTH_CODE_KEY = GLOBAL_REDIS_KEY + "social_auth_codes:";

    // ===================== Spring Cache 缓存组名称 =====================

    /**
     * 演示案例
     */
    String DEMO_CACHE = "demo:cache#60s#10m#20";

    /**
     * 系统配置
     */
    String SYS_CONFIG = "sys_config";

    /**
     * 数据字典
     */
    String SYS_DICT = "sys_dict";

    /**
     * 数据字典类型
     */
    String SYS_DICT_TYPE = "sys_dict_type";

    /**
     * 客户端
     */
    String SYS_CLIENT = GLOBAL_REDIS_KEY + "sys_client#30d";

    /**
     * 用户账户
     */
    String SYS_USER_NAME = "sys_user_name#30d";

    /**
     * 用户昵称
     */
    String SYS_NICKNAME = "sys_nickname#30d";

    /**
     * 部门
     */
    String SYS_DEPT = "sys_dept#30d";

    /**
     * 角色自定义权限
     */
    String SYS_ROLE_CUSTOM = "sys_role_custom#30d";

    /**
     * 部门及以下权限
     */
    String SYS_DEPT_AND_CHILD = "sys_dept_and_child#30d";

    /**
     * 在线用户
     */
    String ONLINE_TOKEN = "online_tokens";

}
