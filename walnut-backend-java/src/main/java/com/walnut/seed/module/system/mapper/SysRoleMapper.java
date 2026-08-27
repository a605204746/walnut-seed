package com.walnut.seed.module.system.mapper;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.walnut.seed.common.mybatis.annotation.DataColumn;
import com.walnut.seed.common.mybatis.annotation.DataPermission;
import com.walnut.seed.common.mybatis.core.mapper.BaseMapperPlus;
import com.walnut.seed.module.system.domain.entity.SysRole;
import com.walnut.seed.module.system.domain.resp.SysRoleResp;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 角色表 数据层
 *
 * @author deepin_sir
 */
public interface SysRoleMapper extends BaseMapperPlus<SysRole, SysRoleResp> {

    /**
     * 构建根据用户ID查询角色ID的SQL子查询
     *
     * @param userId 用户ID
     * @return 查询用户对应角色ID的SQL语句字符串
     */
    default String buildRoleByUserSql(Long userId) {
        return """
                    select role_id from sys_user_role where user_id = %d
                """.formatted(userId);
    }

    /**
     * 分页查询角色列表
     *
     * @param page         分页对象
     * @param queryWrapper 查询条件
     * @return 包含角色信息的分页结果
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "create_dept"),
            @DataColumn(key = "userName", value = "create_by")
    })
    default Page<SysRoleResp> selectPageRoleList(@Param("page") Page<SysRole> page, @Param(Constants.WRAPPER) Wrapper<SysRole> queryWrapper) {
        return this.selectVoPage(page, queryWrapper);
    }

    /**
     * 根据条件查询角色数据
     *
     * @param queryWrapper 查询条件
     * @return 角色数据集合信息
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "create_dept"),
            @DataColumn(key = "userName", value = "create_by")
    })
    default List<SysRoleResp> selectRoleList(@Param(Constants.WRAPPER) Wrapper<SysRole> queryWrapper) {
        return this.selectVoList(queryWrapper);
    }

    /**
     * 根据角色ID集合查询角色数量
     *
     * @param roleIds 角色ID列表
     * @return 匹配的角色数量
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "create_dept"),
            @DataColumn(key = "userName", value = "create_by")
    })
    default long selectRoleCount(List<Long> roleIds) {
        return this.selectCount(new LambdaQueryWrapper<SysRole>().in(SysRole::getId, roleIds));
    }

    /**
     * 根据角色ID查询角色信息
     *
     * @param roleId 角色ID
     * @return 对应的角色信息
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "create_dept"),
            @DataColumn(key = "userName", value = "create_by")
    })
    default SysRoleResp selectRoleById(Long roleId) {
        return this.selectVoById(roleId);
    }

    /**
     * 根据用户ID查询角色
     *
     * @param userId 用户ID
     * @return 角色列表
     */
    default List<SysRoleResp> selectRolesByUserId(Long userId) {
        return this.selectVoList(new LambdaQueryWrapper<SysRole>()
                .select(SysRole::getId, SysRole::getRoleName, SysRole::getRoleKey,
                        SysRole::getRoleSort, SysRole::getDataScope, SysRole::getStatus)
                .inSql(SysRole::getId, this.buildRoleByUserSql(userId)));
    }

}
