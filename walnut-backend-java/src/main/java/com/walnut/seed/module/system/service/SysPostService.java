package com.walnut.seed.module.system.service;
import com.walnut.seed.common.core.domain.PageResult;

import com.walnut.seed.module.system.domain.req.SysPostReq;
import com.walnut.seed.module.system.domain.resp.SysPostResp;

import java.util.List;

/**
 * 岗位信息 服务层
 *
 * @author deepin_sir
 */
public interface SysPostService {

    /**
     * 分页查询岗位列表
     *
     * @param post      查询条件
     * @param pageQuery 分页参数
     * @return 岗位分页列表
     */
    PageResult<SysPostResp> selectPagePostList(SysPostReq req);

    /**
     * 查询岗位信息集合
     *
     * @param post 岗位信息
     * @return 岗位列表
     */
    List<SysPostResp> selectPostList(SysPostReq req);

    /**
     * 查询用户所属岗位组
     *
     * @param userId 用户ID
     * @return 岗位ID
     */
    List<SysPostResp> selectPostsByUserId(Long userId);

    /**
     * 查询所有岗位
     *
     * @return 岗位列表
     */
    List<SysPostResp> selectPostAll();

    /**
     * 通过岗位ID查询岗位信息
     *
     * @param postId 岗位ID
     * @return 角色对象信息
     */
    SysPostResp selectPostById(Long postId);

    /**
     * 根据用户ID获取岗位选择框列表
     *
     * @param userId 用户ID
     * @return 选中岗位ID列表
     */
    List<Long> selectPostListByUserId(Long userId);

    /**
     * 通过岗位ID串查询岗位
     *
     * @param postIds 岗位id串
     * @return 岗位列表信息
     */
    List<SysPostResp> selectPostByIds(List<Long> postIds);

    /**
     * 校验岗位名称
     *
     * @param post 岗位信息
     * @return 结果
     */
    boolean checkPostNameUnique(SysPostReq req);

    /**
     * 校验岗位编码
     *
     * @param post 岗位信息
     * @return 结果
     */
    boolean checkPostCodeUnique(SysPostReq req);

    /**
     * 通过岗位ID查询岗位使用数量
     *
     * @param postId 岗位ID
     * @return 结果
     */
    long countUserPostById(Long postId);

    /**
     * 通过部门ID查询岗位使用数量
     *
     * @param deptId 部门id
     * @return 结果
     */
    long countPostByDeptId(Long deptId);

    /**
     * 删除岗位信息
     *
     * @param postId 岗位ID
     * @return 结果
     */
    int deletePostById(Long postId);

    /**
     * 批量删除岗位信息
     *
     * @param postIds 需要删除的岗位ID
     * @return 结果
     */
    int deletePostByIds(List<Long> postIds);

    /**
     * 新增保存岗位信息
     *
     * @param req 岗位信息
     * @return 结果
     */
    int insertPost(SysPostReq req);

    /**
     * 修改保存岗位信息
     *
     * @param req 岗位信息
     * @return 结果
     */
    int updatePost(SysPostReq req);
}
