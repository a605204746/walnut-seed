package com.walnut.seed.common.core.exception;

/**
 * 业务错误码契约
 * <p>
 * 各模块定义自己的错误码枚举实现本接口，配合 {@link ServiceException} 抛出。
 * 错误码号段划分：
 * <pre>
 * 10000-19999  认证模块（module/web：登录 / 验证码 / 注册 / 客户端）
 * 20000-29999  系统管理（module/system：用户 / 角色 / 部门 / 菜单 / 字典 / 参数）
 * 30000-39999  文件存储（oss）
 * 40000-49999  监控与日志（monitor）
 * 90000-99999  全局通用预留
 * </pre>
 * HTTP 语义层（200/401/403/500 等）保持原义不变，前端依据 401 跳转登录。
 *
 * @author deepin_sir
 */
public interface ErrorCode {

    /**
     * 数字错误码（按模块号段分配）
     */
    int getCode();

    /**
     * i18n 消息 key
     */
    String getKey();
}
