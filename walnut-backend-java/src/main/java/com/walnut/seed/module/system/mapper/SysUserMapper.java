package com.walnut.seed.module.system.mapper;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.walnut.seed.common.mybatis.annotation.DataColumn;
import com.walnut.seed.common.mybatis.annotation.DataPermission;
import com.walnut.seed.common.mybatis.core.mapper.BaseMapperPlus;
import com.walnut.seed.module.system.domain.entity.SysUser;
import com.walnut.seed.module.system.domain.resp.SysUserExportResp;
import com.walnut.seed.module.system.domain.resp.SysUserResp;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 用户表 数据层
 *
 * @author deepin_sir
 */
public interface SysUserMapper extends BaseMapperPlus<SysUser, SysUserResp> {

    /**
     * 分页查询用户列表，并进行数据权限控制
     *
     * @param page         分页参数
     * @param queryWrapper 查询条件
     * @return 分页的用户信息
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "dept_id"),
            @DataColumn(key = "userName", value = "create_by")
    })
    default Page<SysUserResp> selectPageUserList(Page<SysUser> page, Wrapper<SysUser> queryWrapper) {
        return this.selectVoPage(page, queryWrapper);
    }

    /**
     * 查询用户列表，并进行数据权限控制
     *
     * @param queryWrapper 查询条件
     * @return 用户信息集合
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "dept_id"),
            @DataColumn(key = "userName", value = "create_by")
    })
    default List<SysUserResp> selectUserList(Wrapper<SysUser> queryWrapper) {
        return this.selectVoList(queryWrapper);
    }

    /**
     * 根据条件分页查询用户列表
     *
     * @param queryWrapper 查询条件
     * @return 用户信息集合信息
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "d.id"),
            @DataColumn(key = "userName", value = "u.create_by")
    })
    List<SysUserExportResp> selectUserExportList(@Param(Constants.WRAPPER) Wrapper<SysUser> queryWrapper);

    /**
     * 根据条件分页查询已配用户角色列表
     *
     * @param page         分页信息
     * @param queryWrapper 查询条件
     * @return 用户信息集合信息
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "d.id"),
            @DataColumn(key = "userName", value = "u.create_by")
    })
    Page<SysUserResp> selectAllocatedList(@Param("page") Page<SysUser> page, @Param(Constants.WRAPPER) Wrapper<SysUser> queryWrapper);

    /**
     * 根据条件分页查询未分配用户角色列表
     *
     * @param queryWrapper 查询条件
     * @return 用户信息集合信息
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "d.id"),
            @DataColumn(key = "userName", value = "u.create_by")
    })
    Page<SysUserResp> selectUnallocatedList(@Param("page") Page<SysUser> page, @Param(Constants.WRAPPER) Wrapper<SysUser> queryWrapper);

    /**
     * 根据用户ID统计用户数量
     *
     * @param userId 用户ID
     * @return 用户数量
     */
    @DataPermission({
            @DataColumn(key = "deptName", value = "dept_id"),
            @DataColumn(key = "userName", value = "create_by")
    })
    default long countUserById(Long userId) {
        return this.selectCount(new LambdaQueryWrapper<SysUser>().eq(SysUser::getId, userId));
    }

    /**
     * 根据条件更新用户数据
     *
     * @param user          要更新的用户实体
     * @param updateWrapper 更新条件封装器
     * @return 更新操作影响的行数
     */
    @Override
    @DataPermission({
            @DataColumn(key = "deptName", value = "dept_id"),
            @DataColumn(key = "userName", value = "create_by")
    })
    int update(@Param(Constants.ENTITY) SysUser user, @Param(Constants.WRAPPER) Wrapper<SysUser> updateWrapper);

    /**
     * 根据用户ID更新用户数据
     *
     * @param user 要更新的用户实体
     * @return 更新操作影响的行数
     */
    @Override
    @DataPermission({
            @DataColumn(key = "deptName", value = "dept_id"),
            @DataColumn(key = "userName", value = "create_by")
    })
    int updateById(@Param(Constants.ENTITY) SysUser user);

}
