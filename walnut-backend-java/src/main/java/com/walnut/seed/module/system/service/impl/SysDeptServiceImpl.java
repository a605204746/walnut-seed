package com.walnut.seed.module.system.service.impl;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.convert.Convert;
import cn.hutool.core.lang.tree.Tree;
import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.walnut.seed.common.core.constant.CacheNames;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.domain.PageResult;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.*;
import com.walnut.seed.common.mybatis.helper.DataBaseHelper;
import com.walnut.seed.common.redis.utils.RedisUtils;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.entity.SysDept;
import com.walnut.seed.module.system.domain.entity.SysRole;
import com.walnut.seed.module.system.domain.entity.SysUser;
import com.walnut.seed.module.system.domain.req.SysDeptReq;
import com.walnut.seed.module.system.domain.resp.SysDeptResp;
import com.walnut.seed.module.system.mapper.SysDeptMapper;
import com.walnut.seed.module.system.mapper.SysRoleMapper;
import com.walnut.seed.module.system.mapper.SysUserMapper;
import com.walnut.seed.module.system.service.SysDeptService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.util.*;

/**
 * 部门管理 服务实现
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysDeptServiceImpl implements SysDeptService {

    private final SysDeptMapper baseMapper;
    private final SysRoleMapper roleMapper;
    private final SysUserMapper userMapper;

    /**
     * 批量回填部门展示字段（父部门名称、负责人名称）
     */
    private void fillDeptResp(List<SysDeptResp> list) {
        if (CollUtil.isEmpty(list)) {
            return;
        }
        // 批量回填父部门名称
        List<Long> parentIds = list.stream().map(SysDeptResp::getParentId)
            .filter(ObjectUtil::isNotNull).distinct().toList();
        Map<Long, String> parentNames = CollUtil.isEmpty(parentIds)
            ? Collections.emptyMap()
            : StreamUtils.toMap(
                baseMapper.selectList(new LambdaQueryWrapper<SysDept>()
                    .select(SysDept::getId, SysDept::getDeptName)
                    .in(SysDept::getId, parentIds)),
                SysDept::getId, SysDept::getDeptName);

        // 批量回填负责人名称
        List<Long> leaderIds = list.stream().map(SysDeptResp::getLeader)
            .filter(ObjectUtil::isNotNull).distinct().toList();
        Map<Long, String> leaderNames = CollUtil.isEmpty(leaderIds)
            ? Collections.emptyMap()
            : StreamUtils.toMap(
                userMapper.selectList(new LambdaQueryWrapper<SysUser>()
                    .select(SysUser::getId, SysUser::getUserName)
                    .in(SysUser::getId, leaderIds)),
                SysUser::getId, SysUser::getUserName);

        list.forEach(dept -> {
            dept.setParentName(parentNames.get(dept.getParentId()));
            dept.setLeaderName(leaderNames.get(dept.getLeader()));
        });
    }

    @Override
    public PageResult<SysDeptResp> selectPageDeptList(SysDeptReq req) {
        Page<SysDeptResp> page = baseMapper.selectPageDeptList(req.buildPage(), buildQueryWrapper(req));
        fillDeptResp(page.getRecords());
        return PageResult.of(page);
    }

    @Override
    public List<SysDeptResp> selectDeptList(SysDeptReq req) {
        LambdaQueryWrapper<SysDept> lqw = buildQueryWrapper(req);
        List<SysDeptResp> list = baseMapper.selectDeptList(lqw);
        fillDeptResp(list);
        return list;
    }

    @Override
    public List<Tree<Long>> selectDeptTreeList(SysDeptReq req) {
        LambdaQueryWrapper<SysDept> lqw = buildQueryWrapper(req);
        List<SysDeptResp> depts = baseMapper.selectDeptList(lqw);
        return buildDeptTreeSelect(depts);
    }

    private LambdaQueryWrapper<SysDept> buildQueryWrapper(SysDeptReq req) {
        LambdaQueryWrapper<SysDept> lqw = Wrappers.lambdaQuery();
        lqw.eq(SysDept::getDelFlag, SystemConstants.NORMAL);
        lqw.eq(ObjectUtil.isNotNull(req.getId()), SysDept::getId, req.getId());
        lqw.eq(ObjectUtil.isNotNull(req.getParentId()), SysDept::getParentId, req.getParentId());
        lqw.like(StringUtils.isNotBlank(req.getDeptName()), SysDept::getDeptName, req.getDeptName());
        lqw.like(StringUtils.isNotBlank(req.getDeptCategory()), SysDept::getDeptCategory, req.getDeptCategory());
        lqw.eq(StringUtils.isNotBlank(req.getStatus()), SysDept::getStatus, req.getStatus());
        lqw.between(req.getBeginTime() != null && req.getEndTime() != null,
                SysDept::getCreateTime, req.getBeginTime(), req.getEndTime());
        lqw.orderByAsc(SysDept::getAncestors);
        lqw.orderByAsc(SysDept::getParentId);
        lqw.orderByAsc(SysDept::getOrderNum);
        lqw.orderByAsc(SysDept::getId);
        if (ObjectUtil.isNotNull(req.getBelongDeptId())) {
            //部门树搜索
            lqw.and(x -> {
                List<Long> deptIds = baseMapper.selectDeptAndChildById(req.getBelongDeptId());
                x.in(SysDept::getId, deptIds);
            });
        }
        return lqw;
    }

    @Override
    public List<Tree<Long>> buildDeptTreeSelect(List<SysDeptResp> depts) {
        if (CollUtil.isEmpty(depts)) {
            return CollUtil.newArrayList();
        }
        return TreeBuildUtils.buildMultiRoot(
                depts,
                SysDeptResp::getId,
                SysDeptResp::getParentId,
                (node, treeNode) -> treeNode
                        .setId(node.getId())
                        .setParentId(node.getParentId())
                        .setName(node.getDeptName())
                        .setWeight(node.getOrderNum())
                        .putExtra("disabled", SystemConstants.DISABLE.equals(node.getStatus()))
        );
    }

    @Override
    public List<Long> selectDeptListByRoleId(Long roleId) {
        SysRole role = roleMapper.selectById(roleId);
        return baseMapper.selectDeptListByRoleId(roleId, role.getDeptCheckStrictly());
    }

    @Override
    public SysDeptResp selectDeptById(Long deptId) {
        return RedisUtils.getOrLoad(CacheNames.SYS_DEPT + deptId, Duration.ofDays(30), () -> {
            SysDeptResp dept = baseMapper.selectVoById(deptId);
            if (ObjectUtil.isNull(dept)) {
                return null;
            }
            fillDeptResp(List.of(dept));
            return dept;
        });
    }

    @Override
    public List<SysDeptResp> selectDeptByIds(List<Long> deptIds) {
        return baseMapper.selectDeptList(new LambdaQueryWrapper<SysDept>()
                .select(SysDept::getId, SysDept::getDeptName, SysDept::getLeader)
                .eq(SysDept::getStatus, SystemConstants.NORMAL)
                .in(CollUtil.isNotEmpty(deptIds), SysDept::getId, deptIds));
    }

    @Override
    public long selectNormalChildrenDeptById(Long deptId) {
        return baseMapper.selectCount(new LambdaQueryWrapper<SysDept>()
                .eq(SysDept::getStatus, SystemConstants.NORMAL)
                .apply(DataBaseHelper.findInSet(deptId, "ancestors")));
    }

    @Override
    public boolean hasChildByDeptId(Long deptId) {
        return baseMapper.exists(new LambdaQueryWrapper<SysDept>()
                .eq(SysDept::getParentId, deptId));
    }

    @Override
    public boolean checkDeptExistUser(Long deptId) {
        return userMapper.exists(new LambdaQueryWrapper<SysUser>()
                .eq(SysUser::getDeptId, deptId));
    }

    @Override
    public boolean checkDeptNameUnique(SysDeptReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysDept>()
                .eq(SysDept::getDeptName, req.getDeptName())
                .eq(SysDept::getParentId, req.getParentId())
                .ne(ObjectUtil.isNotNull(req.getId()), SysDept::getId, req.getId()));
        return !exist;
    }

    @Override
    public void checkDeptDataScope(Long deptId) {
        if (ObjectUtil.isNull(deptId)) {
            return;
        }
        if (LoginHelper.isSuperAdmin()) {
            return;
        }
        if (baseMapper.countDeptById(deptId) == 0) {
            throw new ServiceException("没有权限访问部门数据！");
        }
    }

    @Override
    public int insertDept(SysDeptReq req) {
        SysDept info = baseMapper.selectById(req.getParentId());
        // 如果父节点不为正常状态,则不允许新增子节点
        if (!SystemConstants.NORMAL.equals(info.getStatus())) {
            throw new ServiceException("部门停用，不允许新增");
        }
        SysDept dept = MapstructUtils.convert(req, SysDept.class);
        dept.setAncestors(info.getAncestors() + StringUtils.SEPARATOR + req.getParentId());
        int row = baseMapper.insert(dept);
        if (row > 0) {
            // 部门树结构变化，清空"部门及以下"缓存
            RedisUtils.deleteByPattern(CacheNames.SYS_DEPT_AND_CHILD + "*");
        }
        return row;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int updateDept(SysDeptReq req) {
        SysDept dept = MapstructUtils.convert(req, SysDept.class);
        SysDept oldDept = baseMapper.selectById(req.getId());
        if (ObjectUtil.isNull(oldDept)) {
            throw new ServiceException("部门不存在，无法修改");
        }
        if (!oldDept.getParentId().equals(req.getParentId())) {
            // 如果是新父部门 则校验是否具有新父部门权限 避免越权
            this.checkDeptDataScope(req.getParentId());
            SysDept newParentDept = baseMapper.selectById(req.getParentId());
            if (ObjectUtil.isNotNull(newParentDept)) {
                String newAncestors = newParentDept.getAncestors() + StringUtils.SEPARATOR + newParentDept.getId();
                String oldAncestors = oldDept.getAncestors();
                dept.setAncestors(newAncestors);
                updateDeptChildren(req.getId(), newAncestors, oldAncestors);
            }
        } else {
            dept.setAncestors(oldDept.getAncestors());
        }
        int result = baseMapper.updateById(dept);
        if (result > 0) {
            RedisUtils.deleteObject(CacheNames.SYS_DEPT + req.getId());
            // 部门树结构变化，清空"部门及以下"缓存
            RedisUtils.deleteByPattern(CacheNames.SYS_DEPT_AND_CHILD + "*");
        }
        // 如果部门状态为启用，且部门祖级列表不为空，且部门祖级列表不等于根部门祖级列表（如果部门祖级列表不等于根部门祖级列表，则说明存在上级部门）
        if (SystemConstants.NORMAL.equals(dept.getStatus())
                && StringUtils.isNotEmpty(dept.getAncestors())
                && !StringUtils.equals(SystemConstants.ROOT_DEPT_ANCESTORS, dept.getAncestors())) {
            // 如果该部门是启用状态，则启用该部门的所有上级部门
            updateParentDeptStatusNormal(dept);
        }
        return result;
    }

    /**
     * 修改该部门的父级部门状态
     *
     * @param dept 当前部门
     */
    private void updateParentDeptStatusNormal(SysDept dept) {
        String ancestors = dept.getAncestors();
        Long[] deptIds = Convert.toLongArray(ancestors);
        baseMapper.update(null, new LambdaUpdateWrapper<SysDept>()
                .set(SysDept::getStatus, SystemConstants.NORMAL)
                .in(SysDept::getId, Arrays.asList(deptIds)));
    }

    /**
     * 修改子元素关系
     *
     * @param deptId       被修改的部门ID
     * @param newAncestors 新的父ID集合
     * @param oldAncestors 旧的父ID集合
     */
    private void updateDeptChildren(Long deptId, String newAncestors, String oldAncestors) {
        List<SysDept> children = baseMapper.selectList(new LambdaQueryWrapper<SysDept>()
                .apply(DataBaseHelper.findInSet(deptId, "ancestors")));
        List<SysDept> list = new ArrayList<>();
        for (SysDept child : children) {
            SysDept dept = new SysDept();
            dept.setId(child.getId());
            dept.setAncestors(child.getAncestors().replaceFirst(oldAncestors, newAncestors));
            list.add(dept);
        }
        if (CollUtil.isNotEmpty(list)) {
            if (baseMapper.updateBatchById(list)) {
                list.forEach(dept -> RedisUtils.deleteObject(CacheNames.SYS_DEPT + dept.getId()));
            }
        }
    }

    @Override
    public int deleteDeptById(Long deptId) {
        int row = baseMapper.deleteById(deptId);
        if (row > 0) {
            RedisUtils.deleteObject(CacheNames.SYS_DEPT + deptId);
            RedisUtils.deleteObject(CacheNames.SYS_DEPT_AND_CHILD + deptId);
        }
        return row;
    }

}
