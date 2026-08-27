package com.walnut.seed.module.system.service.impl;
import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.exception.NotLoginException;
import cn.dev33.satoken.stp.StpUtil;
import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.CacheNames;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.module.system.domain.model.LoginUser;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.StreamUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.entity.SysRole;
import com.walnut.seed.module.system.domain.entity.SysRoleDept;
import com.walnut.seed.module.system.domain.entity.SysRoleMenu;
import com.walnut.seed.module.system.domain.entity.SysUserRole;
import com.walnut.seed.module.system.domain.req.SysRoleReq;
import com.walnut.seed.module.system.domain.resp.SysRoleResp;
import com.walnut.seed.module.system.mapper.SysRoleDeptMapper;
import com.walnut.seed.module.system.mapper.SysRoleMapper;
import com.walnut.seed.module.system.mapper.SysRoleMenuMapper;
import com.walnut.seed.module.system.mapper.SysUserRoleMapper;
import com.walnut.seed.module.system.service.SysRoleService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

/**
 * 角色 业务层处理
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysRoleServiceImpl implements SysRoleService {

    private final SysRoleMapper baseMapper;
    private final SysRoleMenuMapper roleMenuMapper;
    private final SysUserRoleMapper userRoleMapper;
    private final SysRoleDeptMapper roleDeptMapper;

    @Override
    public PageResult<SysRoleResp> selectPageRoleList(SysRoleReq req) {
        Page<SysRoleResp> page = baseMapper.selectPageRoleList(req.buildPage(), this.buildQueryWrapper(req));
        return PageResult.of(page);
    }

    @Override
    public List<SysRoleResp> selectRoleList(SysRoleReq req) {
        return baseMapper.selectRoleList(this.buildQueryWrapper(req));
    }

    private Wrapper<SysRole> buildQueryWrapper(SysRoleReq req) {
        LambdaQueryWrapper<SysRole> wrapper = Wrappers.lambdaQuery();
        wrapper.eq(ObjectUtil.isNotNull(req.getId()), SysRole::getId, req.getId())
            .like(StringUtils.isNotBlank(req.getRoleName()), SysRole::getRoleName, req.getRoleName())
            .eq(StringUtils.isNotBlank(req.getStatus()), SysRole::getStatus, req.getStatus())
            .like(StringUtils.isNotBlank(req.getRoleKey()), SysRole::getRoleKey, req.getRoleKey())
            .between(req.getBeginTime() != null && req.getEndTime() != null,
                SysRole::getCreateTime, req.getBeginTime(), req.getEndTime())
            .orderByAsc(SysRole::getRoleSort).orderByAsc(SysRole::getCreateTime);
        return wrapper;
    }

    @Override
    public List<SysRoleResp> selectRolesByUserId(Long userId) {
        return baseMapper.selectRolesByUserId(userId);
    }

    @Override
    public List<SysRoleResp> selectRolesAuthByUserId(Long userId) {
        List<SysRoleResp> userRoles = baseMapper.selectRolesByUserId(userId);
        List<SysRoleResp> roles = selectRoleAll();
        // 使用HashSet提高查找效率
        Set<Long> userRoleIds = StreamUtils.toSet(userRoles, SysRoleResp::getId);
        for (SysRoleResp role : roles) {
            if (userRoleIds.contains(role.getId())) {
                role.setFlag(true);
            }
        }
        return roles;
    }

    @Override
    public Set<String> selectRolePermissionByUserId(Long userId) {
        List<SysRoleResp> perms = baseMapper.selectRolesByUserId(userId);
        Set<String> permsSet = new HashSet<>();
        for (SysRoleResp perm : perms) {
            if (ObjectUtil.isNotNull(perm)) {
                permsSet.addAll(StringUtils.splitList(perm.getRoleKey().trim()));
            }
        }
        return permsSet;
    }

    @Override
    public List<SysRoleResp> selectRoleAll() {
        return this.selectRoleList(new SysRoleReq());
    }

    @Override
    public List<Long> selectRoleListByUserId(Long userId) {
        List<SysRoleResp> list = baseMapper.selectRolesByUserId(userId);
        return StreamUtils.toList(list, SysRoleResp::getId);
    }

    @Override
    public SysRoleResp selectRoleById(Long roleId) {
        return baseMapper.selectRoleById(roleId);
    }

    @Override
    public List<SysRoleResp> selectRoleByIds(List<Long> roleIds) {
        return baseMapper.selectRoleList(new LambdaQueryWrapper<SysRole>()
            .eq(SysRole::getStatus, SystemConstants.NORMAL)
            .in(CollUtil.isNotEmpty(roleIds), SysRole::getId, roleIds));
    }

    @Override
    public boolean checkRoleNameUnique(SysRoleReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysRole>()
            .eq(SysRole::getRoleName, req.getRoleName())
            .ne(ObjectUtil.isNotNull(req.getId()), SysRole::getId, req.getId()));
        return !exist;
    }

    @Override
    public boolean checkRoleKeyUnique(SysRoleReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysRole>()
            .eq(SysRole::getRoleKey, req.getRoleKey())
            .ne(ObjectUtil.isNotNull(req.getId()), SysRole::getId, req.getId()));
        return !exist;
    }

    @Override
    public void checkRoleAllowed(SysRoleReq req) {
        if (ObjectUtil.isNotNull(req.getId()) && LoginHelper.isSuperAdmin(req.getId())) {
            throw new ServiceException("不允许操作超级管理员角色");
        }
        String[] keys = new String[]{SystemConstants.SUPER_ADMIN_ROLE_KEY, SystemConstants.ADMIN_ROLE_KEY};
        // 新增不允许使用 管理员标识符
        if (ObjectUtil.isNull(req.getId())
            && StringUtils.equalsAny(req.getRoleKey(), keys)) {
            throw new ServiceException("不允许使用系统内置管理员角色标识符!");
        }
        // 修改不允许修改 管理员标识符
        if (ObjectUtil.isNotNull(req.getId())) {
            SysRole sysRole = baseMapper.selectById(req.getId());
            // 如果标识符不相等 判断为修改了管理员标识符
            if (!StringUtils.equals(sysRole.getRoleKey(), req.getRoleKey())) {
                if (StringUtils.equalsAny(sysRole.getRoleKey(), keys)) {
                    throw new ServiceException("不允许修改系统内置管理员角色标识符!");
                } else if (StringUtils.equalsAny(req.getRoleKey(), keys)) {
                    throw new ServiceException("不允许使用系统内置管理员角色标识符!");
                }
            }
        }
    }

    @Override
    public void checkRoleDataScope(Long roleId) {
        if (ObjectUtil.isNull(roleId)) {
            return;
        }
        this.checkRoleDataScope(Collections.singletonList(roleId));
    }

    @Override
    public void checkRoleDataScope(List<Long> roleIds) {
        if (CollUtil.isEmpty(roleIds) || LoginHelper.isSuperAdmin()) {
            return;
        }
        long count = baseMapper.selectRoleCount(roleIds);
        if (count != roleIds.size()) {
            throw new ServiceException("没有权限访问部分角色数据！");
        }
    }

    @Override
    public long countUserRoleByRoleId(Long roleId) {
        return userRoleMapper.selectCount(new LambdaQueryWrapper<SysUserRole>().eq(SysUserRole::getRoleId, roleId));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int insertRole(SysRoleReq req) {
        SysRole role = MapstructUtils.convert(req, SysRole.class);
        // 新增角色信息
        baseMapper.insert(role);
        req.setId(role.getId());
        return insertRoleMenu(req);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int updateRole(SysRoleReq req) {
        SysRole role = MapstructUtils.convert(req, SysRole.class);

        if (SystemConstants.DISABLE.equals(req.getStatus()) && this.countUserRoleByRoleId(req.getId()) > 0) {
            throw new ServiceException("角色已分配，不能禁用!");
        }
        // 修改角色信息
        baseMapper.updateById(role);
        // 删除角色与菜单关联
        roleMenuMapper.delete(new LambdaQueryWrapper<SysRoleMenu>().eq(SysRoleMenu::getRoleId, req.getId()));
        return insertRoleMenu(req);
    }

    @Override
    public int updateRoleStatus(Long roleId, String status) {
        if (SystemConstants.DISABLE.equals(status) && this.countUserRoleByRoleId(roleId) > 0) {
            throw new ServiceException("角色已分配，不能禁用!");
        }
        return baseMapper.update(null,
            new LambdaUpdateWrapper<SysRole>()
                .set(SysRole::getStatus, status)
                .eq(SysRole::getId, roleId));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int authDataScope(SysRoleReq req) {
        SysRole role = MapstructUtils.convert(req, SysRole.class);
        // 修改角色信息
        baseMapper.updateById(role);
        // 删除角色与部门关联
        roleDeptMapper.delete(new LambdaQueryWrapper<SysRoleDept>().eq(SysRoleDept::getRoleId, req.getId()));
        // 新增角色和部门信息（数据权限）
        int rows = insertRoleDept(req);
        RedisUtils.deleteObject(CacheNames.SYS_ROLE_CUSTOM + req.getId());
        return rows;
    }

    /**
     * 新增角色菜单信息
     *
     * @param req 角色对象
     */
    private int insertRoleMenu(SysRoleReq req) {
        int rows = 1;
        // 新增用户与角色管理
        List<SysRoleMenu> list = new ArrayList<>();
        for (Long menuId : req.getMenuIds()) {
            SysRoleMenu rm = new SysRoleMenu();
            rm.setRoleId(req.getId());
            rm.setMenuId(menuId);
            list.add(rm);
        }
        if (CollUtil.isNotEmpty(list)) {
            rows = roleMenuMapper.insertBatch(list) ? list.size() : 0;
        }
        return rows;
    }

    /**
     * 新增角色部门信息(数据权限)
     *
     * @param req 角色对象
     */
    private int insertRoleDept(SysRoleReq req) {
        int rows = 1;
        // 新增角色与部门（数据权限）管理
        List<SysRoleDept> list = new ArrayList<>();
        for (Long deptId : req.getDeptIds()) {
            SysRoleDept rd = new SysRoleDept();
            rd.setRoleId(req.getId());
            rd.setDeptId(deptId);
            list.add(rd);
        }
        if (CollUtil.isNotEmpty(list)) {
            rows = roleDeptMapper.insertBatch(list) ? list.size() : 0;
        }
        return rows;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int deleteRoleById(Long roleId) {
        // 删除角色与菜单关联
        roleMenuMapper.delete(new LambdaQueryWrapper<SysRoleMenu>().eq(SysRoleMenu::getRoleId, roleId));
        // 删除角色与部门关联
        roleDeptMapper.delete(new LambdaQueryWrapper<SysRoleDept>().eq(SysRoleDept::getRoleId, roleId));
        int rows = baseMapper.deleteById(roleId);
        RedisUtils.deleteObject(CacheNames.SYS_ROLE_CUSTOM + roleId);
        return rows;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int deleteRoleByIds(List<Long> roleIds) {
        this.checkRoleDataScope(roleIds);
        List<SysRole> roles = baseMapper.selectByIds(roleIds);
        for (SysRole role : roles) {
            checkRoleAllowed(BeanUtil.toBean(role, SysRoleReq.class));
            if (countUserRoleByRoleId(role.getId()) > 0) {
                throw new ServiceException(String.format("%1$s已分配，不能删除!", role.getRoleName()));
            }
        }
        // 删除角色与菜单关联
        roleMenuMapper.delete(new LambdaQueryWrapper<SysRoleMenu>().in(SysRoleMenu::getRoleId, roleIds));
        // 删除角色与部门关联
        roleDeptMapper.delete(new LambdaQueryWrapper<SysRoleDept>().in(SysRoleDept::getRoleId, roleIds));
        int rows = baseMapper.deleteByIds(roleIds);
        RedisUtils.deleteByPattern(CacheNames.SYS_ROLE_CUSTOM + "*");
        return rows;
    }

    @Override
    public int deleteAuthUser(SysUserRole userRole) {
        if (LoginHelper.getUserId().equals(userRole.getUserId())) {
            throw new ServiceException("不允许修改当前用户角色!");
        }
        int rows = userRoleMapper.delete(new LambdaQueryWrapper<SysUserRole>()
            .eq(SysUserRole::getRoleId, userRole.getRoleId())
            .eq(SysUserRole::getUserId, userRole.getUserId()));
        if (rows > 0) {
            cleanOnlineUser(List.of(userRole.getUserId()));
        }
        return rows;
    }

    @Override
    public int deleteAuthUsers(Long roleId, Long[] userIds) {
        List<Long> ids = List.of(userIds);
        if (ids.contains(LoginHelper.getUserId())) {
            throw new ServiceException("不允许修改当前用户角色!");
        }
        int rows = userRoleMapper.delete(new LambdaQueryWrapper<SysUserRole>()
            .eq(SysUserRole::getRoleId, roleId)
            .in(SysUserRole::getUserId, ids));
        if (rows > 0) {
            cleanOnlineUser(ids);
        }
        return rows;
    }

    @Override
    public int insertAuthUsers(Long roleId, Long[] userIds) {
        // 新增用户与角色管理
        int rows = 1;
        List<Long> ids = List.of(userIds);
        if (ids.contains(LoginHelper.getUserId())) {
            throw new ServiceException("不允许修改当前用户角色!");
        }
        List<SysUserRole> list = StreamUtils.toList(ids, userId -> {
            SysUserRole ur = new SysUserRole();
            ur.setUserId(userId);
            ur.setRoleId(roleId);
            return ur;
        });
        if (CollUtil.isNotEmpty(list)) {
            rows = userRoleMapper.insertBatch(list) ? list.size() : 0;
        }
        if (rows > 0) {
            cleanOnlineUser(ids);
        }
        return rows;
    }

    @Override
    public void cleanOnlineUserByRole(Long roleId) {
        // 如果角色未绑定用户 直接返回
        Long num = userRoleMapper.selectCount(new LambdaQueryWrapper<SysUserRole>().eq(SysUserRole::getRoleId, roleId));
        if (num == 0) {
            return;
        }
        List<String> keys = StpUtil.searchTokenValue("", 0, -1, false);
        if (CollUtil.isEmpty(keys)) {
            return;
        }
        // 角色关联的在线用户量过大会导致redis阻塞卡顿 谨慎操作
        keys.parallelStream().forEach(key -> {
            String token = StringUtils.substringAfterLast(key, ":");
            // 如果已经过期则跳过
            if (StpUtil.stpLogic.getTokenActiveTimeoutByToken(token) < -1) {
                return;
            }
            LoginUser loginUser = LoginHelper.getLoginUser(token);
            if (ObjectUtil.isNull(loginUser) || CollUtil.isEmpty(loginUser.getRoles())) {
                return;
            }
            if (loginUser.getRoles().stream().anyMatch(r -> r.getId().equals(roleId))) {
                try {
                    StpUtil.logoutByTokenValue(token);
                } catch (NotLoginException ignored) {
                }
            }
        });
    }

    @Override
    public void cleanOnlineUser(List<Long> userIds) {
        List<String> keys = StpUtil.searchTokenValue("", 0, -1, false);
        if (CollUtil.isEmpty(keys)) {
            return;
        }
        // 角色关联的在线用户量过大会导致redis阻塞卡顿 谨慎操作
        keys.parallelStream().forEach(key -> {
            String token = StringUtils.substringAfterLast(key, ":");
            // 如果已经过期则跳过
            if (StpUtil.stpLogic.getTokenActiveTimeoutByToken(token) < -1) {
                return;
            }
            LoginUser loginUser = LoginHelper.getLoginUser(token);
            if (ObjectUtil.isNull(loginUser)) {
                return;
            }
            if (userIds.contains(loginUser.getUserId())) {
                try {
                    StpUtil.logoutByTokenValue(token);
                } catch (NotLoginException ignored) {
                }
            }
        });
    }

}
