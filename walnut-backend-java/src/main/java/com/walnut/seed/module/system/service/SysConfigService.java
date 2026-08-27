package com.walnut.seed.module.system.service;

import com.walnut.seed.common.core.domain.PageResult;
import com.walnut.seed.module.system.domain.req.SysConfigReq;
import com.walnut.seed.module.system.domain.resp.SysConfigResp;

import java.util.List;

/**
 * 参数配置 服务层
 *
 * @author deepin_sir
 */
public interface SysConfigService {

    /**
     * 分页查询参数配置列表
     *
     * @param req 查询条件
     * @return 参数配置分页列表
     */
    PageResult<SysConfigResp> selectPageConfigList(SysConfigReq req);

    /**
     * 查询参数配置信息
     *
     * @param configId 参数配置ID
     * @return 参数配置信息
     */
    SysConfigResp selectConfigById(Long configId);

    /**
     * 根据键名查询参数配置信息
     *
     * @param configKey 参数键名
     * @return 参数键值
     */
    String selectConfigByKey(String configKey);

    /**
     * 获取注册开关
     *
     * @return true开启，false关闭
     */
    boolean selectRegisterEnabled();

    /**
     * 查询参数配置列表
     *
     * @param config 参数配置信息
     * @return 参数配置集合
     */
    List<SysConfigResp> selectConfigList(SysConfigReq config);

    /**
     * 新增参数配置
     *
     * @param req 参数配置信息
     * @return 结果
     */
    String insertConfig(SysConfigReq req);

    /**
     * 修改参数配置
     *
     * @param req 参数配置信息
     * @return 结果
     */
    String updateConfig(SysConfigReq req);

    /**
     * 批量删除参数信息
     *
     * @param configIds 需要删除的参数ID
     */
    void deleteConfigByIds(List<Long> configIds);

    /**
     * 重置参数缓存数据
     */
    void resetConfigCache();

    /**
     * 校验参数键名是否唯一
     *
     * @param config 参数信息
     * @return 结果
     */
    boolean checkConfigKeyUnique(SysConfigReq config);

}
