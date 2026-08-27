package com.walnut.seed.module.system.domain.resp;

import lombok.Data;

import java.util.List;

/**
 * 用户信息
 *
 * @author deepin_sir
 */
@Data
public class SysUserInfoResp {

    /**
     * 用户信息
     */
    private SysUserResp user;

    /**
     * 角色ID列表
     */
    private List<Long> roleIds;

    /**
     * 角色列表
     */
    private List<SysRoleResp> roles;

    /**
     * 岗位ID列表
     */
    private List<Long> postIds;

    /**
     * 岗位列表
     */
    private List<SysPostResp> posts;

}
