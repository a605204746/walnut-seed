package com.walnut.seed.module.system.domain.model;

import com.walnut.seed.common.core.domain.model.BaseLoginUser;
import com.walnut.seed.module.system.domain.dto.PostDTO;
import com.walnut.seed.module.system.domain.dto.RoleDTO;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.io.Serial;
import java.util.List;
import java.util.Set;

/**
 * 登录用户身份权限（系统模块扩展）
 *
 * @author deepin_sir
 */
@Data
@NoArgsConstructor
@EqualsAndHashCode(callSuper = true)
public class LoginUser extends BaseLoginUser {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 部门ID
     */
    private Long deptId;

    /**
     * 部门类别编码
     */
    private String deptCategory;

    /**
     * 部门名
     */
    private String deptName;

    /**
     * 用户昵称
     */
    private String nickname;

    /**
     * 菜单权限
     */
    private Set<String> menuPermission;

    /**
     * 角色权限
     */
    private Set<String> rolePermission;

    /**
     * 角色对象
     */
    private List<RoleDTO> roles;

    /**
     * 岗位对象
     */
    private List<PostDTO> posts;

    /**
     * 数据权限 当前角色ID
     */
    private Long roleId;

    /**
     * 客户端
     */
    private String clientKey;

}
