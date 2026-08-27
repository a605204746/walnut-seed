package com.walnut.seed.module.system.service.impl;
import com.walnut.seed.common.core.domain.PageResult;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.convert.Convert;
import cn.hutool.core.util.ArrayUtil;
import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.walnut.seed.common.core.constant.CacheNames;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.module.system.domain.dto.UserDTO;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.service.UserService;
import com.walnut.seed.common.core.utils.*;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.entity.SysUser;
import com.walnut.seed.module.system.domain.entity.SysDept;
import com.walnut.seed.module.system.domain.entity.SysUserPost;
import com.walnut.seed.module.system.domain.entity.SysUserRole;
import com.walnut.seed.module.system.domain.req.SysUserReq;
import com.walnut.seed.module.system.domain.resp.SysPostResp;
import com.walnut.seed.module.system.domain.resp.SysRoleResp;
import com.walnut.seed.module.system.domain.resp.SysUserExportResp;
import com.walnut.seed.module.system.domain.resp.SysUserResp;
import com.walnut.seed.module.system.mapper.*;
import com.walnut.seed.module.system.service.SysUserService;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

/**
 * 用户 业务层处理
 *
 * @author deepin_sir
 */
@Slf4j
@RequiredArgsConstructor
@Service
public class SysUserServiceImpl implements SysUserService, UserService {

    private final SysUserMapper baseMapper;
    private final SysDeptMapper deptMapper;
    private final SysRoleMapper roleMapper;
    private final SysPostMapper postMapper;
    private final SysUserRoleMapper userRoleMapper;
    private final SysUserPostMapper userPostMapper;

    /**
     * 批量回填用户展示字段（部门名称）
     */
    private void fillUserResp(List<SysUserResp> list) {
        if (CollUtil.isEmpty(list)) {
            return;
        }
        List<Long> deptIds = list.stream().map(SysUserResp::getDeptId)
            .filter(ObjectUtil::isNotNull).distinct().toList();
        Map<Long, String> deptNames = CollUtil.isEmpty(deptIds)
            ? Collections.emptyMap()
            : StreamUtils.toMap(
                deptMapper.selectList(new LambdaQueryWrapper<SysDept>()
                    .select(SysDept::getId, SysDept::getDeptName)
                    .in(SysDept::getId, deptIds)),
                SysDept::getId, SysDept::getDeptName);

        list.forEach(user -> user.setDeptName(deptNames.get(user.getDeptId())));
    }

    @Override
    public PageResult<SysUserResp> selectPageUserList(SysUserReq req) {
        Page<SysUserResp> page = baseMapper.selectPageUserList(req.buildPage(), this.buildQueryWrapper(req));
        fillUserResp(page.getRecords());
        return PageResult.of(page);
    }

    @Override
    public List<SysUserExportResp> selectUserExportList(SysUserReq req) {
        QueryWrapper<SysUser> wrapper = Wrappers.query();
        wrapper.eq("u.del_flag", SystemConstants.NORMAL)
            .like(StringUtils.isNotBlank(req.getUserName()), "u.user_name", req.getUserName())
            .like(StringUtils.isNotBlank(req.getNickName()), "u.nick_name", req.getNickName())
            .eq(StringUtils.isNotBlank(req.getStatus()), "u.status", req.getStatus())
            .like(StringUtils.isNotBlank(req.getPhonenumber()), "u.phonenumber", req.getPhonenumber())
            .between(req.getBeginTime() != null && req.getEndTime() != null,
                "u.create_time", req.getBeginTime(), req.getEndTime())
            .and(ObjectUtil.isNotNull(req.getDeptId()), w -> {
                List<Long> deptIds = deptMapper.selectDeptAndChildById(req.getDeptId());
                w.in("u.dept_id", deptIds);
            }).orderByAsc("u.id");
        return baseMapper.selectUserExportList(wrapper);
    }

    private Wrapper<SysUser> buildQueryWrapper(SysUserReq req) {
        LambdaQueryWrapper<SysUser> wrapper = Wrappers.lambdaQuery();
        wrapper.eq(SysUser::getDelFlag, SystemConstants.NORMAL)
            .eq(ObjectUtil.isNotNull(req.getId()), SysUser::getId, req.getId())
            .in(StringUtils.isNotBlank(req.getUserIds()), SysUser::getId, StringUtils.splitTo(req.getUserIds(), Convert::toLong))
            .like(StringUtils.isNotBlank(req.getUserName()), SysUser::getUserName, req.getUserName())
            .like(StringUtils.isNotBlank(req.getNickName()), SysUser::getNickName, req.getNickName())
            .eq(StringUtils.isNotBlank(req.getStatus()), SysUser::getStatus, req.getStatus())
            .like(StringUtils.isNotBlank(req.getPhonenumber()), SysUser::getPhonenumber, req.getPhonenumber())
            .between(req.getBeginTime() != null && req.getEndTime() != null,
                SysUser::getCreateTime, req.getBeginTime(), req.getEndTime())
            .and(ObjectUtil.isNotNull(req.getDeptId()), w -> {
                List<Long> ids = deptMapper.selectDeptAndChildById(req.getDeptId());
                w.in(SysUser::getDeptId, ids);
            }).orderByAsc(SysUser::getId);
        if (StringUtils.isNotBlank(req.getExcludeUserIds())) {
            wrapper.notIn(SysUser::getId, StringUtils.splitTo(req.getExcludeUserIds(), Convert::toLong));
        }
        return wrapper;
    }

    @Override
    public PageResult<SysUserResp> selectAllocatedList(SysUserReq req) {
        QueryWrapper<SysUser> wrapper = Wrappers.query();
        wrapper.eq("u.del_flag", SystemConstants.NORMAL)
            .eq(ObjectUtil.isNotNull(req.getRoleId()), "r.id", req.getRoleId())
            .like(StringUtils.isNotBlank(req.getUserName()), "u.user_name", req.getUserName())
            .eq(StringUtils.isNotBlank(req.getStatus()), "u.status", req.getStatus())
            .like(StringUtils.isNotBlank(req.getPhonenumber()), "u.phonenumber", req.getPhonenumber())
            .orderByAsc("u.id");
        Page<SysUserResp> page = baseMapper.selectAllocatedList(req.buildPage(), wrapper);
        fillUserResp(page.getRecords());
        return PageResult.of(page);
    }

    @Override
    public PageResult<SysUserResp> selectUnallocatedList(SysUserReq req) {
        List<Long> userIds = userRoleMapper.selectUserIdsByRoleId(req.getRoleId());
        QueryWrapper<SysUser> wrapper = Wrappers.query();
        wrapper.eq("u.del_flag", SystemConstants.NORMAL)
            .and(w -> w.ne("r.id", req.getRoleId()).or().isNull("r.id"))
            .notIn(CollUtil.isNotEmpty(userIds), "u.id", userIds)
            .like(StringUtils.isNotBlank(req.getUserName()), "u.user_name", req.getUserName())
            .like(StringUtils.isNotBlank(req.getPhonenumber()), "u.phonenumber", req.getPhonenumber())
            .orderByAsc("u.id");
        Page<SysUserResp> page = baseMapper.selectUnallocatedList(req.buildPage(), wrapper);
        fillUserResp(page.getRecords());
        return PageResult.of(page);
    }

    @Override
    public SysUserResp selectUserByUserName(String userName) {
        return baseMapper.selectVoOne(new LambdaQueryWrapper<SysUser>().eq(SysUser::getUserName, userName));
    }

    @Override
    public SysUserResp selectUserByPhonenumber(String phonenumber) {
        return baseMapper.selectVoOne(new LambdaQueryWrapper<SysUser>().eq(SysUser::getPhonenumber, phonenumber));
    }

    @Override
    public SysUserResp selectUserById(Long userId) {
        SysUserResp user = baseMapper.selectVoById(userId);
        if (ObjectUtil.isNull(user)) {
            return user;
        }
        user.setRoles(roleMapper.selectRolesByUserId(user.getId()));
        fillUserResp(List.of(user));
        return user;
    }

    @Override
    public List<SysUserResp> selectUserByIds(List<Long> userIds, Long deptId) {
        return baseMapper.selectUserList(new LambdaQueryWrapper<SysUser>()
            .select(SysUser::getId, SysUser::getUserName, SysUser::getNickName)
            .eq(SysUser::getStatus, SystemConstants.NORMAL)
            .eq(ObjectUtil.isNotNull(deptId), SysUser::getDeptId, deptId)
            .in(CollUtil.isNotEmpty(userIds), SysUser::getId, userIds));
    }

    @Override
    public String selectUserRoleGroup(Long userId) {
        List<SysRoleResp> list = roleMapper.selectRolesByUserId(userId);
        if (CollUtil.isEmpty(list)) {
            return StringUtils.EMPTY;
        }
        return StreamUtils.join(list, SysRoleResp::getRoleName);
    }

    @Override
    public String selectUserPostGroup(Long userId) {
        List<SysPostResp> list = postMapper.selectPostsByUserId(userId);
        if (CollUtil.isEmpty(list)) {
            return StringUtils.EMPTY;
        }
        return StreamUtils.join(list, SysPostResp::getPostName);
    }

    @Override
    public boolean checkUserNameUnique(SysUserReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysUser>()
            .eq(SysUser::getUserName, req.getUserName())
            .ne(ObjectUtil.isNotNull(req.getId()), SysUser::getId, req.getId()));
        return !exist;
    }

    @Override
    public boolean checkPhoneUnique(SysUserReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysUser>()
            .eq(SysUser::getPhonenumber, req.getPhonenumber())
            .ne(ObjectUtil.isNotNull(req.getId()), SysUser::getId, req.getId()));
        return !exist;
    }

    @Override
    public boolean checkEmailUnique(SysUserReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysUser>()
            .eq(SysUser::getEmail, req.getEmail())
            .ne(ObjectUtil.isNotNull(req.getId()), SysUser::getId, req.getId()));
        return !exist;
    }

    @Override
    public void checkUserAllowed(Long userId) {
        if (ObjectUtil.isNotNull(userId) && LoginHelper.isSuperAdmin(userId)) {
            throw new ServiceException("不允许操作超级管理员用户");
        }
    }

    @Override
    public void checkUserDataScope(Long userId) {
        if (ObjectUtil.isNull(userId)) {
            return;
        }
        if (LoginHelper.isSuperAdmin()) {
            return;
        }
        if (baseMapper.countUserById(userId) == 0) {
            throw new ServiceException("没有权限访问用户数据！");
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int insertUser(SysUserReq req) {
        SysUser sysUser = MapstructUtils.convert(req, SysUser.class);
        // 新增用户信息
        int rows = baseMapper.insert(sysUser);
        req.setId(sysUser.getId());
        // 新增用户岗位关联
        insertUserPost(req, false);
        // 新增用户与角色管理
        insertUserRole(req, false);
        return rows;
    }

    @Override
    public boolean registerUser(SysUserReq req) {
        SysUser sysUser = MapstructUtils.convert(req, SysUser.class);
        sysUser.setCreateBy(0L);
        sysUser.setUpdateBy(0L);
        return baseMapper.insert(sysUser) > 0;
    }

    /**
     * 修改保存用户信息
     *
     * @param req 用户信息
     * @return 结果
     */
    @Override
    @CacheEvict(cacheNames = CacheNames.SYS_NICKNAME, key = "#req.id")
    @Transactional(rollbackFor = Exception.class)
    public int updateUser(SysUserReq req) {
        // 新增用户与角色管理
        insertUserRole(req, true);
        // 新增用户与岗位管理
        insertUserPost(req, true);
        SysUser sysUser = MapstructUtils.convert(req, SysUser.class);
        // 防止错误更新后导致的数据误删除
        int flag = baseMapper.updateById(sysUser);
        if (flag < 1) {
            throw new ServiceException("修改用户{}信息失败", req.getUserName());
        }
        return flag;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void insertUserAuth(Long userId, Long[] roleIds) {
        insertUserRole(userId, roleIds, true);
    }

    /**
     * 修改用户状态
     *
     * @param userId 用户ID
     * @param status 账号状态
     * @return 结果
     */
    @Override
    public int updateUserStatus(Long userId, String status) {
        return baseMapper.update(null,
            new LambdaUpdateWrapper<SysUser>()
                .set(SysUser::getStatus, status)
                .eq(SysUser::getId, userId));
    }

    /**
     * 修改用户基本信息
     *
     * @param req 用户信息
     * @return 结果
     */
    @CacheEvict(cacheNames = CacheNames.SYS_NICKNAME, key = "#req.id")
    @Override
    public int updateUserProfile(SysUserReq req) {
        return baseMapper.update(null,
            new LambdaUpdateWrapper<SysUser>()
                .set(ObjectUtil.isNotNull(req.getNickName()), SysUser::getNickName, req.getNickName())
                .set(SysUser::getPhonenumber, req.getPhonenumber())
                .set(SysUser::getEmail, req.getEmail())
                .set(SysUser::getSex, req.getSex())
                .eq(SysUser::getId, req.getId()));
    }

    /**
     * 修改用户头像
     *
     * @param userId 用户ID
     * @param avatar 头像地址
     * @return 结果
     */
    @Override
    public boolean updateUserAvatar(Long userId, String avatarUrl) {
        return baseMapper.update(null,
            new LambdaUpdateWrapper<SysUser>()
                .set(SysUser::getAvatar, avatarUrl)
                .eq(SysUser::getId, userId)) > 0;
    }

    /**
     * 重置用户密码
     *
     * @param userId   用户ID
     * @param password 密码
     * @return 结果
     */
    @Override
    public int resetUserPwd(Long userId, String password) {
        return baseMapper.update(null,
            new LambdaUpdateWrapper<SysUser>()
                .set(SysUser::getPassword, password)
                .eq(SysUser::getId, userId));
    }

    /**
     * 新增用户角色信息
     *
     * @param req  用户对象
     * @param clear 清除已存在的关联数据
     */
    private void insertUserRole(SysUserReq req, boolean clear) {
        this.insertUserRole(req.getId(), req.getRoleIds(), clear);
    }

    /**
     * 新增用户岗位信息
     *
     * @param req  用户对象
     * @param clear 清除已存在的关联数据
     */
    private void insertUserPost(SysUserReq req, boolean clear) {
        Long[] postIdArr = req.getPostIds();
        if (ArrayUtil.isEmpty(postIdArr)) {
            return;
        }
        List<Long> postIds = Arrays.asList(postIdArr);

        // 校验是否有权限操作这些岗位（含数据权限控制）
        if (postMapper.selectPostCount(postIds) != postIds.size()) {
            throw new ServiceException("没有权限访问岗位的数据");
        }

        // 是否清除旧的用户岗位绑定
        if (clear) {
            userPostMapper.delete(new LambdaQueryWrapper<SysUserPost>().eq(SysUserPost::getUserId, req.getId()));
        }

        // 构建用户岗位关联列表并批量插入
        List<SysUserPost> list = StreamUtils.toList(postIds,
            postId -> {
                SysUserPost up = new SysUserPost();
                up.setUserId(req.getId());
                up.setPostId(postId);
                return up;
            });
        userPostMapper.insertBatch(list);
    }

    /**
     * 新增用户角色信息
     *
     * @param userId  用户ID
     * @param roleIds 角色组
     * @param clear   清除已存在的关联数据
     */
    private void insertUserRole(Long userId, Long[] roleIds, boolean clear) {
        if (ArrayUtil.isEmpty(roleIds)) {
            return;
        }

        List<Long> roleList = new ArrayList<>(Arrays.asList(roleIds));

        // 非超级管理员，禁止包含超级管理员角色
        if (!LoginHelper.isSuperAdmin(userId)) {
            roleList.remove(SystemConstants.SUPER_ADMIN_ID);
        }

        // 移除超管角色后若无剩余角色，说明仅选了超管角色且不允许分配，显式报错
        if (roleList.isEmpty()) {
            throw new ServiceException("不允许为普通用户分配超级管理员角色，请至少选择一个其他角色");
        }

        // 校验是否有权限访问这些角色（含数据权限控制）
        if (roleMapper.selectRoleCount(roleList) != roleList.size()) {
            throw new ServiceException("没有权限访问角色的数据");
        }

        // 是否清除原有绑定
        if (clear) {
            userRoleMapper.delete(new LambdaQueryWrapper<SysUserRole>().eq(SysUserRole::getUserId, userId));
        }

        // 批量插入用户-角色关联
        List<SysUserRole> list = StreamUtils.toList(roleList,
            roleId -> {
                SysUserRole ur = new SysUserRole();
                ur.setUserId(userId);
                ur.setRoleId(roleId);
                return ur;
            });
        userRoleMapper.insertBatch(list);
    }

    /**
     * 通过用户ID删除用户
     *
     * @param userId 用户ID
     * @return 结果
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public int deleteUserById(Long userId) {
        // 删除用户与角色关联
        userRoleMapper.delete(new LambdaQueryWrapper<SysUserRole>().eq(SysUserRole::getUserId, userId));
        // 删除用户与岗位表
        userPostMapper.delete(new LambdaQueryWrapper<SysUserPost>().eq(SysUserPost::getUserId, userId));
        // 防止更新失败导致的数据删除
        int flag = baseMapper.deleteById(userId);
        if (flag < 1) {
            throw new ServiceException("删除用户失败!");
        }
        return flag;
    }

    /**
     * 批量删除用户信息
     *
     * @param userIds 需要删除的用户ID
     * @return 结果
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public int deleteUserByIds(Long[] userIds) {
        for (Long userId : userIds) {
            checkUserAllowed(userId);
            checkUserDataScope(userId);
        }
        List<Long> ids = List.of(userIds);
        // 删除用户与角色关联
        userRoleMapper.delete(new LambdaQueryWrapper<SysUserRole>().in(SysUserRole::getUserId, ids));
        // 删除用户与岗位表
        userPostMapper.delete(new LambdaQueryWrapper<SysUserPost>().in(SysUserPost::getUserId, ids));
        // 防止更新失败导致的数据删除
        int flag = baseMapper.deleteByIds(ids);
        if (flag < 1) {
            throw new ServiceException("删除用户失败!");
        }
        return flag;
    }

    /**
     * 通过部门id查询当前部门所有用户
     *
     * @param deptId 部门ID
     * @return 用户信息集合信息
     */
    @Override
    public List<SysUserResp> selectUserListByDept(Long deptId) {
        LambdaQueryWrapper<SysUser> lqw = Wrappers.lambdaQuery();
        lqw.eq(SysUser::getDeptId, deptId);
        lqw.orderByAsc(SysUser::getId);
        List<SysUserResp> list = baseMapper.selectVoList(lqw);
        fillUserResp(list);
        return list;
    }

    /**
     * 通过用户ID查询用户账户
     *
     * @param userId 用户ID
     * @return 用户账户
     */
    @Cacheable(cacheNames = CacheNames.SYS_USER_NAME, key = "#userId")
    @Override
    public String selectUserNameById(Long userId) {
        SysUser sysUser = baseMapper.selectOne(new LambdaQueryWrapper<SysUser>()
            .select(SysUser::getUserName).eq(SysUser::getId, userId));
        return ObjectUtils.notNullGetter(sysUser, SysUser::getUserName);
    }

    /**
     * 通过用户ID查询用户昵称
     *
     * @param userId 用户ID
     * @return 用户昵称
     */
    @Override
    @Cacheable(cacheNames = CacheNames.SYS_NICKNAME, key = "#userId")
    public String selectNicknameById(Long userId) {
        SysUser sysUser = baseMapper.selectOne(new LambdaQueryWrapper<SysUser>()
            .select(SysUser::getNickName).eq(SysUser::getId, userId));
        return ObjectUtils.notNullGetter(sysUser, SysUser::getNickName);
    }

    /**
     * 通过用户ID查询用户昵称
     *
     * @param userIds 用户ID 多个用逗号隔开
     * @return 用户昵称
     */
    @Override
    public String selectNicknameByIds(String userIds) {
        List<String> list = new ArrayList<>();
        for (Long id : StringUtils.splitTo(userIds, Convert::toLong)) {
            String nickname = SpringUtils.getAopProxy(this).selectNicknameById(id);
            if (StringUtils.isNotBlank(nickname)) {
                list.add(nickname);
            }
        }
        return StringUtils.joinComma(list);
    }

    /**
     * 通过用户ID查询用户手机号
     *
     * @param userId 用户id
     * @return 用户手机号
     */
    @Override
    public String selectPhonenumberById(Long userId) {
        SysUser sysUser = baseMapper.selectOne(new LambdaQueryWrapper<SysUser>()
            .select(SysUser::getPhonenumber).eq(SysUser::getId, userId));
        return ObjectUtils.notNullGetter(sysUser, SysUser::getPhonenumber);
    }

    /**
     * 通过用户ID查询用户邮箱
     *
     * @param userId 用户id
     * @return 用户邮箱
     */
    @Override
    public String selectEmailById(Long userId) {
        SysUser sysUser = baseMapper.selectOne(new LambdaQueryWrapper<SysUser>()
            .select(SysUser::getEmail).eq(SysUser::getId, userId));
        return ObjectUtils.notNullGetter(sysUser, SysUser::getEmail);
    }

    /**
     * 通过用户ID查询用户列表
     *
     * @param userIds 用户ids
     * @return 用户列表
     */
    @Override
    public List<UserDTO> selectListByIds(List<Long> userIds) {
        if (CollUtil.isEmpty(userIds)) {
            return List.of();
        }
        List<SysUserResp> list = baseMapper.selectVoList(new LambdaQueryWrapper<SysUser>()
            .select(SysUser::getId, SysUser::getDeptId, SysUser::getUserName,
                SysUser::getNickName, SysUser::getUserType, SysUser::getEmail,
                SysUser::getPhonenumber, SysUser::getSex, SysUser::getStatus,
                SysUser::getCreateTime)
            .eq(SysUser::getStatus, SystemConstants.NORMAL)
            .in(SysUser::getId, userIds));
        return BeanUtil.copyToList(list, UserDTO.class);
    }

    /**
     * 通过角色ID查询用户ID
     *
     * @param roleIds 角色ids
     * @return 用户ids
     */
    @Override
    public List<Long> selectUserIdsByRoleIds(List<Long> roleIds) {
        if (CollUtil.isEmpty(roleIds)) {
            return List.of();
        }
        List<SysUserRole> userRoles = userRoleMapper.selectList(
            new LambdaQueryWrapper<SysUserRole>().in(SysUserRole::getRoleId, roleIds));
        return StreamUtils.toList(userRoles, SysUserRole::getUserId);
    }

    /**
     * 通过角色ID查询用户
     *
     * @param roleIds 角色ids
     * @return 用户
     */
    @Override
    public List<UserDTO> selectUsersByRoleIds(List<Long> roleIds) {
        if (CollUtil.isEmpty(roleIds)) {
            return List.of();
        }

        // 通过角色ID获取用户角色信息
        List<SysUserRole> userRoles = userRoleMapper.selectList(
            new LambdaQueryWrapper<SysUserRole>().in(SysUserRole::getRoleId, roleIds));

        // 获取用户ID列表
        Set<Long> userIds = StreamUtils.toSet(userRoles, SysUserRole::getUserId);

        return this.selectListByIds(new ArrayList<>(userIds));
    }

    /**
     * 通过部门ID查询用户
     *
     * @param deptIds 部门ids
     * @return 用户
     */
    @Override
    public List<UserDTO> selectUsersByDeptIds(List<Long> deptIds) {
        if (CollUtil.isEmpty(deptIds)) {
            return List.of();
        }
        List<SysUserResp> list = baseMapper.selectVoList(new LambdaQueryWrapper<SysUser>()
            .select(SysUser::getId, SysUser::getUserName, SysUser::getNickName, SysUser::getEmail, SysUser::getPhonenumber)
            .eq(SysUser::getStatus, SystemConstants.NORMAL)
            .in(SysUser::getDeptId, deptIds));
        return BeanUtil.copyToList(list, UserDTO.class);
    }

    /**
     * 通过岗位ID查询用户
     *
     * @param postIds 岗位ids
     * @return 用户
     */
    @Override
    public List<UserDTO> selectUsersByPostIds(List<Long> postIds) {
        if (CollUtil.isEmpty(postIds)) {
            return List.of();
        }

        // 通过岗位ID获取用户岗位信息
        List<SysUserPost> userPosts = userPostMapper.selectList(
            new LambdaQueryWrapper<SysUserPost>().in(SysUserPost::getPostId, postIds));

        // 获取用户ID列表
        Set<Long> userIds = StreamUtils.toSet(userPosts, SysUserPost::getUserId);

        return this.selectListByIds(new ArrayList<>(userIds));
    }

    /**
     * 根据用户 ID 列表查询用户昵称映射关系
     *
     * @param userIds 用户 ID 列表
     * @return Map，其中 key 为用户 ID，value 为对应的用户昵称
     */
    @Override
    public Map<Long, String> selectUserNicksByIds(List<Long> userIds) {
        if (CollUtil.isEmpty(userIds)) {
            return Collections.emptyMap();
        }
        List<SysUser> list = baseMapper.selectList(
            new LambdaQueryWrapper<SysUser>()
                .select(SysUser::getId, SysUser::getNickName)
                .in(SysUser::getId, userIds)
        );
        return StreamUtils.toMap(list, SysUser::getId, SysUser::getNickName);
    }

    @Override
    public Map<Long, String> selectUserNameMap(List<Long> userIds) {
        if (CollUtil.isEmpty(userIds)) {
            return Collections.emptyMap();
        }
        List<SysUser> list = baseMapper.selectList(
            new LambdaQueryWrapper<SysUser>()
                .select(SysUser::getId, SysUser::getUserName)
                .in(SysUser::getId, userIds)
        );
        return StreamUtils.toMap(list, SysUser::getId, SysUser::getUserName);
    }

}
