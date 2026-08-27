package com.walnut.seed.module.system.service;
import com.walnut.seed.common.core.domain.PageResult;

import com.walnut.seed.module.system.domain.req.SysUserReq;
import com.walnut.seed.module.system.domain.resp.SysUserExportResp;
import com.walnut.seed.module.system.domain.resp.SysUserResp;

import java.util.List;
import java.util.Map;

/**
 * 用户 业务层
 *
 * @author deepin_sir
 */
public interface SysUserService {


    /**
     * 根据条件分页查询用户列表
     *
     * @param req 用户信息
     * @return 用户信息
     */
    PageResult<SysUserResp> selectPageUserList(SysUserReq req);

    /**
     * 导出用户列表
     *
     * @param user 用户信息
     * @return 用户信息集合信息
     */
    List<SysUserExportResp> selectUserExportList(SysUserReq user);

    /**
     * 根据条件分页查询已分配用户角色列表
     *
     * @param req 用户信息
     * @return 用户信息集合信息
     */
    PageResult<SysUserResp> selectAllocatedList(SysUserReq req);

    /**
     * 根据条件分页查询未分配用户角色列表
     *
     * @param req 用户信息
     * @return 用户信息集合信息
     */
    PageResult<SysUserResp> selectUnallocatedList(SysUserReq req);

    /**
     * 通过用户名查询用户
     *
     * @param userName 用户名
     * @return 用户对象信息
     */
    SysUserResp selectUserByUserName(String userName);

    /**
     * 通过手机号查询用户
     *
     * @param phonenumber 手机号
     * @return 用户对象信息
     */
    SysUserResp selectUserByPhonenumber(String phonenumber);

    /**
     * 通过用户ID查询用户
     *
     * @param userId 用户ID
     * @return 用户对象信息
     */
    SysUserResp selectUserById(Long userId);

    /**
     * 通过用户ID串查询用户
     *
     * @param userIds 用户ID串
     * @param deptId  部门id
     * @return 用户列表信息
     */
    List<SysUserResp> selectUserByIds(List<Long> userIds, Long deptId);

    /**
     * 根据用户ID查询用户所属角色组
     *
     * @param userId 用户ID
     * @return 结果
     */
    String selectUserRoleGroup(Long userId);

    /**
     * 根据用户ID查询用户所属岗位组
     *
     * @param userId 用户ID
     * @return 结果
     */
    String selectUserPostGroup(Long userId);

    /**
     * 校验用户账号是否唯一
     *
     * @param user 用户信息
     * @return 结果
     */
    boolean checkUserNameUnique(SysUserReq user);

    /**
     * 校验手机号码是否唯一
     *
     * @param user 用户信息
     * @return 结果
     */
    boolean checkPhoneUnique(SysUserReq user);

    /**
     * 校验email是否唯一
     *
     * @param user 用户信息
     * @return 结果
     */
    boolean checkEmailUnique(SysUserReq user);

    /**
     * 校验用户是否允许操作
     *
     * @param userId 用户ID
     */
    void checkUserAllowed(Long userId);

    /**
     * 校验用户是否有数据权限
     *
     * @param userId 用户id
     */
    void checkUserDataScope(Long userId);

    /**
     * 新增用户信息
     *
     * @param user 用户信息
     * @return 结果
     */
    int insertUser(SysUserReq user);

    /**
     * 注册用户信息
     *
     * @param user 用户信息
     * @return 结果
     */
    boolean registerUser(SysUserReq user);

    /**
     * 修改用户信息
     *
     * @param user 用户信息
     * @return 结果
     */
    int updateUser(SysUserReq user);

    /**
     * 用户授权角色
     *
     * @param userId  用户ID
     * @param roleIds 角色组
     */
    void insertUserAuth(Long userId, Long[] roleIds);

    /**
     * 修改用户状态
     *
     * @param userId 用户ID
     * @param status 账号状态
     * @return 结果
     */
    int updateUserStatus(Long userId, String status);

    /**
     * 修改用户基本信息
     *
     * @param user 用户信息
     * @return 结果
     */
    int updateUserProfile(SysUserReq user);

    /**
     * 修改用户头像
     *
     * @param userId 用户ID
     * @param avatarUrl 头像地址
     * @return 结果
     */
    boolean updateUserAvatar(Long userId, String avatarUrl);

    /**
     * 重置用户密码
     *
     * @param userId   用户ID
     * @param password 密码
     * @return 结果
     */
    int resetUserPwd(Long userId, String password);

    /**
     * 通过用户ID删除用户
     *
     * @param userId 用户ID
     * @return 结果
     */
    int deleteUserById(Long userId);

    /**
     * 批量删除用户信息
     *
     * @param userIds 需要删除的用户ID
     * @return 结果
     */
    int deleteUserByIds(Long[] userIds);

    /**
     * 通过部门id查询当前部门所有用户
     *
     * @param deptId 部门id
     * @return 结果
     */
    List<SysUserResp> selectUserListByDept(Long deptId);

    /**
     * 批量查询用户账号映射
     *
     * @param userIds 用户 ID 列表
     * @return key 为用户 ID，value 为登录账号
     */
    Map<Long, String> selectUserNameMap(List<Long> userIds);
}
