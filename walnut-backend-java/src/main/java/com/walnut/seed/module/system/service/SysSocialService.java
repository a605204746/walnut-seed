package com.walnut.seed.module.system.service;

import com.walnut.seed.module.system.domain.req.SysSocialReq;
import com.walnut.seed.module.system.domain.resp.SysSocialResp;

import java.util.List;

/**
 * 社会化关系Service接口
 *
 * @author deepin_sir
 */
public interface SysSocialService {


    /**
     * 查询社会化关系
     */
    SysSocialResp queryById(String id);

    /**
     * 查询社会化关系列表
     */
    List<SysSocialResp> queryList(SysSocialReq req);

    /**
     * 查询社会化关系列表
     */
    List<SysSocialResp> queryListByUserId(Long userId);

    /**
     * 新增授权关系
     */
    Boolean insertByBo(SysSocialReq req);

    /**
     * 更新社会化关系
     */
    Boolean updateByBo(SysSocialReq req);

    /**
     * 删除社会化关系信息
     */
    Boolean deleteWithValidById(Long id);


    /**
     * 根据 authId 查询
     */
    List<SysSocialResp> selectByAuthId(String authId);


}
