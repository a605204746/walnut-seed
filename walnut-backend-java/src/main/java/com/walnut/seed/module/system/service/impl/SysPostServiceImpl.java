package com.walnut.seed.module.system.service.impl;
import com.walnut.seed.common.core.domain.PageResult;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.ObjectUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.MapstructUtils;
import com.walnut.seed.common.core.utils.StreamUtils;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.module.system.domain.entity.SysDept;
import com.walnut.seed.module.system.domain.entity.SysPost;
import com.walnut.seed.module.system.domain.entity.SysUserPost;
import com.walnut.seed.module.system.domain.req.SysPostReq;
import com.walnut.seed.module.system.domain.resp.SysPostResp;
import com.walnut.seed.module.system.mapper.SysDeptMapper;
import com.walnut.seed.module.system.mapper.SysPostMapper;
import com.walnut.seed.module.system.mapper.SysUserPostMapper;
import com.walnut.seed.module.system.service.SysPostService;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * 岗位信息 服务层处理
 *
 * @author deepin_sir
 */
@RequiredArgsConstructor
@Service
public class SysPostServiceImpl implements SysPostService {

    private final SysPostMapper baseMapper;
    private final SysDeptMapper deptMapper;
    private final SysUserPostMapper userPostMapper;

    /**
     * 批量回填岗位展示字段（部门名）
     */
    private void fillPostResp(List<SysPostResp> list) {
        if (CollUtil.isEmpty(list)) {
            return;
        }
        List<Long> deptIds = list.stream().map(SysPostResp::getDeptId)
            .filter(ObjectUtil::isNotNull).distinct().toList();
        if (CollUtil.isEmpty(deptIds)) {
            return;
        }
        List<SysDept> depts = deptMapper.selectList(new LambdaQueryWrapper<SysDept>()
            .select(SysDept::getId, SysDept::getDeptName)
            .in(SysDept::getId, deptIds));
        Map<Long, String> deptNames = StreamUtils.toMap(depts, SysDept::getId, SysDept::getDeptName);
        list.forEach(post -> post.setDeptName(deptNames.get(post.getDeptId())));
    }

    @Override
    public PageResult<SysPostResp> selectPagePostList(SysPostReq req) {
        Page<SysPostResp> page = baseMapper.selectPagePostList(req.buildPage(), buildQueryWrapper(req));
        fillPostResp(page.getRecords());
        return PageResult.of(page);
    }

    @Override
    public List<SysPostResp> selectPostList(SysPostReq req) {
        List<SysPostResp> list = baseMapper.selectVoList(buildQueryWrapper(req));
        fillPostResp(list);
        return list;
    }

    @Override
    public List<SysPostResp> selectPostsByUserId(Long userId) {
        return baseMapper.selectPostsByUserId(userId);
    }

    /**
     * 根据查询条件构建查询包装器
     *
     * @param req 查询条件对象
     * @return 构建好的查询包装器
     */
    private LambdaQueryWrapper<SysPost> buildQueryWrapper(SysPostReq req) {
        LambdaQueryWrapper<SysPost> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(StringUtils.isNotBlank(req.getPostCode()), SysPost::getPostCode, req.getPostCode())
            .like(StringUtils.isNotBlank(req.getPostCategory()), SysPost::getPostCategory, req.getPostCategory())
            .like(StringUtils.isNotBlank(req.getPostName()), SysPost::getPostName, req.getPostName())
            .eq(StringUtils.isNotBlank(req.getStatus()), SysPost::getStatus, req.getStatus())
            .between(req.getBeginTime() != null && req.getEndTime() != null,
                SysPost::getCreateTime, req.getBeginTime(), req.getEndTime())
            .orderByAsc(SysPost::getPostSort);
        if (ObjectUtil.isNotNull(req.getDeptId())) {
            //优先单部门搜索
            wrapper.eq(SysPost::getDeptId, req.getDeptId());
        } else if (ObjectUtil.isNotNull(req.getBelongDeptId())) {
            //部门树搜索
            wrapper.and(x -> {
                List<Long> deptIds = deptMapper.selectDeptAndChildById(req.getBelongDeptId());
                x.in(SysPost::getDeptId, deptIds);
            });
        }
        return wrapper;
    }

    @Override
    public List<SysPostResp> selectPostAll() {
        List<SysPostResp> list = baseMapper.selectVoList(new QueryWrapper<>());
        fillPostResp(list);
        return list;
    }

    @Override
    public SysPostResp selectPostById(Long postId) {
        SysPostResp post = baseMapper.selectVoById(postId);
        fillPostResp(post == null ? null : List.of(post));
        return post;
    }

    @Override
    public List<Long> selectPostListByUserId(Long userId) {
        List<SysPostResp> list = baseMapper.selectPostsByUserId(userId);
        return StreamUtils.toList(list, SysPostResp::getId);
    }

    @Override
    public List<SysPostResp> selectPostByIds(List<Long> postIds) {
        List<SysPostResp> list = baseMapper.selectVoList(new LambdaQueryWrapper<SysPost>()
            .select(SysPost::getId, SysPost::getPostName, SysPost::getPostCode)
            .eq(SysPost::getStatus, SystemConstants.NORMAL)
            .in(CollUtil.isNotEmpty(postIds), SysPost::getId, postIds));
        fillPostResp(list);
        return list;
    }

    @Override
    public boolean checkPostNameUnique(SysPostReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysPost>()
            .eq(SysPost::getPostName, req.getPostName())
            .eq(SysPost::getDeptId, req.getDeptId())
            .ne(ObjectUtil.isNotNull(req.getId()), SysPost::getId, req.getId()));
        return !exist;
    }

    @Override
    public boolean checkPostCodeUnique(SysPostReq req) {
        boolean exist = baseMapper.exists(new LambdaQueryWrapper<SysPost>()
            .eq(SysPost::getPostCode, req.getPostCode())
            .ne(ObjectUtil.isNotNull(req.getId()), SysPost::getId, req.getId()));
        return !exist;
    }

    @Override
    public long countUserPostById(Long postId) {
        return userPostMapper.selectCount(new LambdaQueryWrapper<SysUserPost>().eq(SysUserPost::getPostId, postId));
    }

    @Override
    public long countPostByDeptId(Long deptId) {
        return baseMapper.selectCount(new LambdaQueryWrapper<SysPost>().eq(SysPost::getDeptId, deptId));
    }

    @Override
    public int deletePostById(Long postId) {
        return baseMapper.deleteById(postId);
    }

    @Override
    public int deletePostByIds(List<Long> postIds) {
        List<SysPost> list = baseMapper.selectByIds(postIds);
        for (SysPost post : list) {
            if (this.countUserPostById(post.getId()) > 0) {
                throw new ServiceException("{}已分配，不能删除!", post.getPostName());
            }
        }
        return baseMapper.deleteByIds(postIds);
    }

    @Override
    public int insertPost(SysPostReq req) {
        SysPost post = MapstructUtils.convert(req, SysPost.class);
        return baseMapper.insert(post);
    }

    @Override
    public int updatePost(SysPostReq req) {
        SysPost post = MapstructUtils.convert(req, SysPost.class);
        return baseMapper.updateById(post);
    }

}
