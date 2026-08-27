package com.walnut.seed.module.system.service;

import com.walnut.seed.common.core.domain.PageResult;
import com.walnut.seed.module.system.domain.req.SysClientReq;
import com.walnut.seed.module.system.domain.resp.SysClientResp;

import java.util.Collection;
import java.util.List;

/**
 * 客户端管理Service接口
 *
 * @author deepin_sir
 * @date 2023-06-18
 */
public interface SysClientService {

    /**
     * 查询客户端管理
     */
    SysClientResp queryById(Long id);

    /**
     * 查询客户端信息基于客户端id
     */
    SysClientResp queryByClientId(String clientId);

    /**
     * 查询客户端管理列表
     */
    PageResult<SysClientResp> queryPageList(SysClientReq req);

    /**
     * 查询客户端管理列表
     */
    List<SysClientResp> queryList(SysClientReq req);

    /**
     * 新增客户端管理
     */
    Boolean insertByBo(SysClientReq req);

    /**
     * 修改客户端管理
     */
    Boolean updateByBo(SysClientReq req);

    /**
     * 修改状态
     */
    int updateClientStatus(String clientId, String status);

    /**
     * 校验并批量删除客户端管理信息
     */
    Boolean deleteWithValidByIds(Collection<Long> ids, Boolean isValid);

    /**
     * 校验客户端key是否唯一
     *
     * @param client 客户端信息
     * @return 结果
     */
    boolean checkClickKeyUnique(SysClientReq client);
}
